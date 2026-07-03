from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.user import PassLevelSetting
from app.schemas.user import PassLevelSettingOut, PassLevelSettingUpdate


router = APIRouter()


@router.get("", response_model=list[PassLevelSettingOut])
def list_pass_settings(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[PassLevelSettingOut]:
    return list(db.scalars(select(PassLevelSetting).order_by(PassLevelSetting.level.asc())).all())


@router.patch("/{setting_id}", response_model=PassLevelSettingOut)
def update_pass_setting(
    setting_id: int,
    payload: PassLevelSettingUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> PassLevelSettingOut:
    setting = db.get(PassLevelSetting, setting_id)
    if setting is None:
        raise HTTPException(status_code=404, detail="Pass setting not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(setting, field, value)

    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting
