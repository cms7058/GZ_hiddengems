from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.spot import ScenicSpot
from app.models.user import PassLevelSetting
from app.schemas.pagination import Page
from app.schemas.user import PassLevelSettingCreate, PassLevelSettingOut, PassLevelSettingUpdate
from app.services.pagination import paginated_scalars
from app.services.pass_levels import ensure_pass_level_marker_color_column


router = APIRouter()


@router.get("", response_model=Page[PassLevelSettingOut])
def list_pass_settings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[PassLevelSettingOut]:
    ensure_pass_level_marker_color_column(db)
    return paginated_scalars(db, select(PassLevelSetting).order_by(PassLevelSetting.level.asc()), page, page_size)


@router.post("", response_model=PassLevelSettingOut, status_code=201)
def create_pass_setting(
    payload: PassLevelSettingCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> PassLevelSettingOut:
    ensure_pass_level_marker_color_column(db)
    existing = db.scalar(select(PassLevelSetting).where(PassLevelSetting.level == payload.level))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Pass level already exists")

    setting = PassLevelSetting(**payload.model_dump())
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


@router.patch("/{setting_id}", response_model=PassLevelSettingOut)
def update_pass_setting(
    setting_id: int,
    payload: PassLevelSettingUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> PassLevelSettingOut:
    ensure_pass_level_marker_color_column(db)
    setting = db.get(PassLevelSetting, setting_id)
    if setting is None:
        raise HTTPException(status_code=404, detail="Pass setting not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(setting, field, value)

    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


@router.delete("/{setting_id}", status_code=204)
def delete_pass_setting(
    setting_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    ensure_pass_level_marker_color_column(db)
    setting = db.get(PassLevelSetting, setting_id)
    if setting is None:
        raise HTTPException(status_code=404, detail="Pass setting not found")
    linked_spot = db.scalar(
        select(ScenicSpot.id).where(ScenicSpot.recommendation_level == setting.level).limit(1)
    )
    if linked_spot is not None:
        raise HTTPException(status_code=409, detail="Reassign linked spots before deleting this pass level")

    db.delete(setting)
    db.commit()
