from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.integration import IntegrationSetting
from app.schemas.integration import IntegrationGroupOut, IntegrationGroupUpdate, IntegrationSettingOut
from app.services.integrations import GROUP_META, mask_secret


router = APIRouter()


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
