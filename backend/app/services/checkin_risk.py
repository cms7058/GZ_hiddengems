"""Server-side route-based checks for detecting implausible check-ins."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Optional
from urllib.parse import urlencode
from urllib.request import urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.spot import ScenicSpot
from app.models.user import CheckinRecord, MiniProgramUser
from app.core.config import settings
from app.services.integrations import get_group_config


class RouteServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckinRiskConfig:
    web_service_key: str
    base_url: str
    warn_ratio: float
    suspicious_ratio: float
    warning_limit: int
    suspicious_limit: int
    watch_limit: int
    repeat_window_hours: int

    @property
    def route_service_configured(self) -> bool:
        return bool(self.web_service_key and self.base_url)


@dataclass(frozen=True)
class RouteEstimate:
    distance_meters: int
    duration_seconds: int


@dataclass(frozen=True)
class RiskEvaluation:
    status: str
    reason: str
    previous_checkin_id: Optional[int] = None
    route: Optional[RouteEstimate] = None
    elapsed_seconds: Optional[int] = None
    travel_time_ratio: Optional[float] = None
    disable_permission: bool = False
    notice: Optional[str] = None


def _number(config: dict[str, str], key: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(config.get(key, default))
    except (TypeError, ValueError):
        return default
    return value if minimum <= value <= maximum else default


def get_checkin_risk_config(db: Session) -> CheckinRiskConfig:
    config = get_group_config(db, "checkin_risk")
    warn_ratio = _number(config, "CHECKIN_ROUTE_WARN_RATIO", 0.70, 0.01, 1.0)
    suspicious_ratio = _number(config, "CHECKIN_ROUTE_SUSPICIOUS_RATIO", 0.90, warn_ratio, 1.0)
    return CheckinRiskConfig(
        web_service_key=(config.get("TENCENT_LBS_WEB_SERVICE_KEY") or settings.tencent_lbs_web_service_key).strip(),
        base_url=(config.get("TENCENT_LBS_BASE_URL") or settings.tencent_lbs_base_url).strip().rstrip("/"),
        warn_ratio=warn_ratio,
        suspicious_ratio=suspicious_ratio,
        warning_limit=int(_number(config, "CHECKIN_WARNING_LIMIT", settings.checkin_warning_limit, 1, 999)),
        suspicious_limit=int(_number(config, "CHECKIN_SUSPICIOUS_LIMIT", settings.checkin_suspicious_limit, 1, 999)),
        watch_limit=int(_number(config, "CHECKIN_WATCH_LIMIT", settings.checkin_watch_limit, 1, 999)),
        repeat_window_hours=int(_number(config, "CHECKIN_REPEAT_WINDOW_HOURS", settings.checkin_repeat_window_hours, 1, 720)),
    )


def get_driving_route(
    config: CheckinRiskConfig,
    origin_latitude: float,
    origin_longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> RouteEstimate:
    if not config.route_service_configured:
        raise RouteServiceError("腾讯地图 WebServiceKey 尚未配置")
    query = urlencode(
        {
            "from": f"{origin_latitude:.6f},{origin_longitude:.6f}",
            "to": f"{target_latitude:.6f},{target_longitude:.6f}",
            "key": config.web_service_key,
        }
    )
    url = f"{config.base_url}/ws/direction/v1/driving/?{query}"
    try:
        with urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as error:  # The provider returns several HTTP error formats.
        raise RouteServiceError(f"腾讯地图路线请求失败：{error}") from error
    if not isinstance(data, dict) or data.get("status") != 0:
        message = data.get("message") if isinstance(data, dict) else "未知响应"
        raise RouteServiceError(f"腾讯地图路线请求失败：{message}")
    routes = ((data.get("result") or {}).get("routes") or [])
    if not routes or not isinstance(routes[0], dict):
        raise RouteServiceError("腾讯地图未返回驾车路线")
    route = routes[0]
    try:
        return RouteEstimate(distance_meters=int(route["distance"]), duration_seconds=max(int(route["duration"]), 1))
    except (KeyError, TypeError, ValueError) as error:
        raise RouteServiceError("腾讯地图路线数据格式无效") from error


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _remaining_notice(kind: str, count: int, limit: int) -> Optional[str]:
    remaining = limit - count
    if 1 <= remaining <= 3:
        return f"本次打卡被标记为{kind}，再出现 {remaining} 次将自动暂停打卡权限。"
    return None


def evaluate_checkin_risk(
    db: Session,
    user: MiniProgramUser,
    spot: ScenicSpot,
    latitude: float,
    longitude: float,
    now: Optional[datetime] = None,
) -> RiskEvaluation:
    """Evaluate route plausibility before persisting a new check-in record.

    Scenic spot coordinates are normalized to GCJ-02 at admin write time. WeChat
    locations and Tencent driving routes use the same coordinate system.
    """
    now = now or datetime.now(timezone.utc)
    config = get_checkin_risk_config(db)
    previous = db.scalar(
        select(CheckinRecord)
        .where(CheckinRecord.user_id == user.id, CheckinRecord.status == "approved")
        .order_by(CheckinRecord.created_at.desc(), CheckinRecord.id.desc())
    )
    if previous is None:
        return RiskEvaluation(status="normal", reason="首次成功打卡，无历史路线可核验。")

    try:
        previous_latitude = float(previous.latitude)
        previous_longitude = float(previous.longitude)
    except (TypeError, ValueError):
        return RiskEvaluation(
            status="unavailable",
            reason="上一条打卡缺少有效坐标，未完成路线核验。",
            previous_checkin_id=previous.id,
        )

    elapsed_seconds = max(0, int((now - _aware(previous.created_at)).total_seconds()))
    if previous.spot_id == spot.id and elapsed_seconds <= config.repeat_window_hours * 3600:
        user.checkin_watch_count += 1
        disabled = user.checkin_watch_count >= config.watch_limit
        return RiskEvaluation(
            status="watch",
            reason=f"{config.repeat_window_hours} 小时内重复打卡同一秘境，已记录为重点关注。",
            previous_checkin_id=previous.id,
            elapsed_seconds=elapsed_seconds,
            disable_permission=disabled,
            notice=_remaining_notice("重点关注", user.checkin_watch_count, config.watch_limit),
        )

    try:
        route = get_driving_route(config, previous_latitude, previous_longitude, spot.latitude, spot.longitude)
    except RouteServiceError as error:
        return RiskEvaluation(
            status="unavailable",
            reason=f"未完成路线核验：{error}",
            previous_checkin_id=previous.id,
            elapsed_seconds=elapsed_seconds,
        )

    ratio = elapsed_seconds / route.duration_seconds
    if ratio < config.warn_ratio:
        user.checkin_warning_count += 1
        disabled = user.checkin_warning_count >= config.warning_limit
        return RiskEvaluation(
            status="warning",
            reason=f"距上次成功打卡仅 {elapsed_seconds // 60} 分钟，低于驾车预计时间的 {config.warn_ratio:.0%}。",
            previous_checkin_id=previous.id,
            route=route,
            elapsed_seconds=elapsed_seconds,
            travel_time_ratio=ratio,
            disable_permission=disabled,
            notice=_remaining_notice("路线时间警告", user.checkin_warning_count, config.warning_limit),
        )
    if ratio < config.suspicious_ratio:
        user.checkin_suspicious_count += 1
        disabled = user.checkin_suspicious_count >= config.suspicious_limit
        return RiskEvaluation(
            status="suspicious",
            reason=f"距上次成功打卡的时间为驾车预计时间的 {ratio:.0%}，已标记为可疑。",
            previous_checkin_id=previous.id,
            route=route,
            elapsed_seconds=elapsed_seconds,
            travel_time_ratio=ratio,
            disable_permission=disabled,
            notice=_remaining_notice("可疑打卡", user.checkin_suspicious_count, config.suspicious_limit),
        )
    return RiskEvaluation(
        status="normal",
        reason="路线时间核验通过。",
        previous_checkin_id=previous.id,
        route=route,
        elapsed_seconds=elapsed_seconds,
        travel_time_ratio=ratio,
    )
