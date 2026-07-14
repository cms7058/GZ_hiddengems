from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.integration import IntegrationSetting
from app.models.spot import ScenicSpot
from app.schemas.integration import IntegrationGroupOut, IntegrationGroupUpdate, IntegrationSettingOut
from app.services.integrations import GROUP_META, get_group_config, get_object_storage_config, mask_secret
from app.services.media_storage import AliyunOssMediaStorage, MediaStorageError
from app.services.qweather import QWeatherClient


router = APIRouter()


@router.post("/weather/test")
def test_weather_connection(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    client = QWeatherClient(get_group_config(db, "weather"))
    if not client.is_configured:
        raise HTTPException(status_code=400, detail="QWeather is not fully configured")

    spot = db.scalars(
        select(ScenicSpot)
        .where(ScenicSpot.is_active.is_(True), ScenicSpot.review_status == "approved")
        .order_by(ScenicSpot.id)
    ).first()
    if spot is None:
        raise HTTPException(status_code=400, detail="Create and approve a scenic spot before testing weather")

    weather = client.get_weather_now(spot.longitude, spot.latitude, "zh")
    alerts = client.get_weather_alerts(spot.longitude, spot.latitude, "zh")
    weather_error = _qweather_error(weather)
    alerts_error = _qweather_error(alerts)
    if weather_error:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "QWeather real-time weather request failed",
                "auth_mode": client.auth_mode,
                "spot": spot.name_zh,
                "weather_error": weather_error,
                "alerts_error": alerts_error,
            },
        )

    now = weather.get("now") or {}
    return {
        "success": True,
        "auth_mode": client.auth_mode,
        "spot": spot.name_zh,
        "location": {"longitude": spot.longitude, "latitude": spot.latitude},
        "weather": {"text": now.get("text"), "temp": now.get("temp"), "obs_time": now.get("obsTime")},
        "alert_count": len(alerts.get("alerts") or []),
        "alerts_error": alerts_error,
    }


def _qweather_error(response: object) -> Optional[str]:
    if not isinstance(response, dict) or not response.get("error"):
        return None
    body = response.get("body")
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            return str(error.get("detail") or error.get("title") or response.get("error"))
        return str(body.get("message") or body.get("detail") or response.get("error"))
    return str(response.get("error"))


@router.post("/object-storage/test")
def test_object_storage_connection(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict[str, str]:
    config = get_object_storage_config(db)
    if config["provider"] != "aliyun_oss":
        raise HTTPException(status_code=400, detail="Set storage provider to aliyun_oss before testing")
    try:
        return AliyunOssMediaStorage(config).test_connection()
    except MediaStorageError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("", response_model=list[IntegrationGroupOut])
def list_integration_settings(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[IntegrationGroupOut]:
    rows = db.scalars(
        select(IntegrationSetting).order_by(IntegrationSetting.group, IntegrationSetting.sort_order)
    ).all()
    grouped: dict[str, list[IntegrationSettingOut]] = {group: [] for group in GROUP_META}
    for row in rows:
        value = mask_secret(row.value) if row.is_secret else row.value
        grouped.setdefault(row.group, []).append(
            IntegrationSettingOut(
                id=row.id,
                group=row.group,
                key=row.key,
                value=value,
                label_zh=row.label_zh,
                label_en=row.label_en,
                input_type=row.input_type,
                is_secret=row.is_secret,
                sort_order=row.sort_order,
                is_configured=bool(row.value),
            )
        )
    return [
        IntegrationGroupOut(
            group=group,
            settings=grouped.get(group, []),
            **meta,
        )
        for group, meta in GROUP_META.items()
    ]


@router.patch("/{group}", response_model=IntegrationGroupOut)
def update_integration_settings(
    group: str,
    payload: IntegrationGroupUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> IntegrationGroupOut:
    rows = db.scalars(select(IntegrationSetting).where(IntegrationSetting.group == group)).all()
    by_key = {row.key: row for row in rows}
    if group == "mini_program":
        merged = {key: row.value or "" for key, row in by_key.items()}
        merged.update({key: value or "" for key, value in payload.settings.items() if key in by_key})
        try:
            open_hour = int(merged.get("PUBLIC_API_OPEN_HOUR", "8"))
            close_hour = int(merged.get("PUBLIC_API_CLOSE_HOUR", "24"))
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Service hours must be integers") from error
        if not (0 <= open_hour < close_hour <= 24):
            raise HTTPException(status_code=400, detail="Service hours must satisfy 0 <= start < end <= 24")
    if group == "object_storage":
        provider_row = by_key.get("MEDIA_STORAGE_PROVIDER")
        provider = (
            payload.settings.get("MEDIA_STORAGE_PROVIDER")
            or (provider_row.value if provider_row else "")
            or "local"
        ).strip().lower()
        if provider not in {"local", "aliyun_oss"}:
            raise HTTPException(status_code=400, detail="Storage provider must be local or aliyun_oss")
    for key, value in payload.settings.items():
        row = by_key.get(key)
        if row is None:
            continue
        if row.is_secret and value is None:
            continue
        row.value = value or ""
        db.add(row)
    db.commit()
    return next(item for item in list_integration_settings(db, current_admin) if item.group == group)
