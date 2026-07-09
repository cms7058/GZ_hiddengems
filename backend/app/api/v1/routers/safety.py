from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.spot import ScenicSpot
from app.services.integrations import get_group_config
from app.services.qweather import QWeatherClient


router = APIRouter()


@router.get("/spots/{spot_id}/safety")
def get_spot_safety(
    spot_id: int,
    lang: str = Query(default="zh-CN"),
    db: Session = Depends(get_db),
) -> dict:
    spot = db.get(ScenicSpot, spot_id)
    if spot is None or not spot.is_active or spot.review_status != "approved":
        raise HTTPException(status_code=404, detail="Spot not found")

    qweather_lang = "en" if lang == "en-US" else "zh"
    qweather_client = QWeatherClient(get_group_config(db, "weather"))
    if not qweather_client.is_configured:
        return {
            "configured": False,
            "source": "QWeather",
            "message": "QWeather is not configured",
            "weather": None,
            "alerts": [],
            "river_warning": {
                "level": "unknown",
                "summary": "暂未接入官方水文数据，请以当地水利、气象和应急管理部门发布为准。",
                "river_name": spot.river_name,
                "upstream_location": _upstream_location(spot),
                "upstream_weather": None,
                "upstream_alerts": [],
            },
        }

    weather = qweather_client.get_weather_now(spot.longitude, spot.latitude, qweather_lang)
    alerts = qweather_client.get_weather_alerts(spot.longitude, spot.latitude, qweather_lang)
    upstream_weather = _get_upstream_weather(spot, qweather_client, qweather_lang)
    upstream_alerts = _get_upstream_alerts(spot, qweather_client, qweather_lang)
    alert_items = alerts.get("alerts", []) if isinstance(alerts, dict) else []
    upstream_alert_items = upstream_alerts.get("alerts", []) if isinstance(upstream_alerts, dict) else []
    now = weather.get("now") if isinstance(weather, dict) else None

    return {
        "configured": True,
        "source": "QWeather",
        "weather": now,
        "weather_update_time": weather.get("updateTime") if isinstance(weather, dict) else None,
        "alerts": alert_items,
        "attributions": _collect_attributions(weather, alerts, upstream_weather, upstream_alerts),
        "river_warning": {
            "level": _estimate_river_risk(
                now,
                alert_items + upstream_alert_items,
                upstream_weather.get("now") if upstream_weather else None,
            ),
            "summary": "当前为气象和预警聚合判断，河流洪水、水位和临时管制仍以官方水文及地方发布为准。",
            "river_name": spot.river_name,
            "upstream_location": _upstream_location(spot),
            "upstream_weather": _normalize_upstream_weather(upstream_weather),
            "upstream_alerts": upstream_alert_items,
        },
    }


def _get_upstream_weather(spot: ScenicSpot, qweather_client: QWeatherClient, lang: str) -> Optional[dict]:
    if spot.river_upstream_latitude is None or spot.river_upstream_longitude is None:
        return None
    return qweather_client.get_weather_now(
        spot.river_upstream_longitude,
        spot.river_upstream_latitude,
        lang,
    )


def _get_upstream_alerts(spot: ScenicSpot, qweather_client: QWeatherClient, lang: str) -> Optional[dict]:
    if spot.river_upstream_latitude is None or spot.river_upstream_longitude is None:
        return None
    return qweather_client.get_weather_alerts(
        spot.river_upstream_longitude,
        spot.river_upstream_latitude,
        lang,
    )


def _upstream_location(spot: ScenicSpot) -> Optional[dict]:
    if spot.river_upstream_latitude is None or spot.river_upstream_longitude is None:
        return None
    return {
        "latitude": spot.river_upstream_latitude,
        "longitude": spot.river_upstream_longitude,
    }


def _normalize_upstream_weather(response: Optional[dict]) -> Optional[dict]:
    if not isinstance(response, dict):
        return None
    now = response.get("now")
    if not now:
        return None
    return {
        "weather": now,
        "update_time": response.get("updateTime"),
    }


def _collect_attributions(*responses: dict) -> list[str]:
    attributions: list[str] = []
    for response in responses:
        if not isinstance(response, dict):
            continue
        refer = response.get("refer") or {}
        metadata = response.get("metadata") or {}
        attributions.extend(refer.get("sources") or [])
        attributions.extend(metadata.get("attributions") or [])
    return list(dict.fromkeys(attributions))


def _estimate_river_risk(weather: Optional[dict], alerts: list[dict], upstream_weather: Optional[dict] = None) -> str:
    alert_text = " ".join(
        [
            str(item.get("headline") or "")
            + str(item.get("description") or "")
            + str((item.get("eventType") or {}).get("name") or "")
            for item in alerts
        ]
    )
    if any(keyword in alert_text for keyword in ["暴雨", "洪水", "山洪", "强降雨", "地质灾害"]):
        return "high"
    try:
        precip = float((weather or {}).get("precip") or 0)
    except (TypeError, ValueError):
        precip = 0
    try:
        upstream_precip = float((upstream_weather or {}).get("precip") or 0)
    except (TypeError, ValueError):
        upstream_precip = 0
    if max(precip, upstream_precip) >= 10:
        return "medium"
    return "low"
