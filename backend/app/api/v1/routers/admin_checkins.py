from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.user import CheckinRecord
from app.schemas.pagination import Page
from app.schemas.user import CheckinRecordOut, CheckinReviewUpdate
from app.services.pagination import build_page, paginated_scalars
from app.services.memberships import sync_user_membership_by_points
from app.services.pass_levels import get_active_pass_settings_by_level, get_checkin_points_for_level


router = APIRouter()


def checkin_to_out(record: CheckinRecord) -> CheckinRecordOut:
    return CheckinRecordOut(
        id=record.id,
        user_id=record.user_id,
        nickname=record.user.nickname,
        spot_id=record.spot_id,
        spot_name_zh=record.spot.name_zh,
        status=record.status,
        latitude=record.latitude,
        longitude=record.longitude,
        image_url=record.image_url,
        note=record.note,
        review_note=record.review_note,
        awarded_explore_points=record.awarded_explore_points,
    )


@router.get("", response_model=Page[CheckinRecordOut])
def list_checkins(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[CheckinRecordOut]:
    result = paginated_scalars(
        db,
        select(CheckinRecord)
        .options(joinedload(CheckinRecord.user), joinedload(CheckinRecord.spot))
        .order_by(CheckinRecord.id.desc()),
        page,
        page_size,
    )
    return build_page(
        [checkin_to_out(record) for record in result.items],
        result.total,
        result.page,
        result.page_size,
    )


@router.patch("/{checkin_id}/review", response_model=CheckinRecordOut)
def review_checkin(
    checkin_id: int,
    payload: CheckinReviewUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> CheckinRecordOut:
    record = db.scalar(
        select(CheckinRecord)
        .options(joinedload(CheckinRecord.user), joinedload(CheckinRecord.spot))
        .where(CheckinRecord.id == checkin_id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Checkin record not found")

    was_approved = record.status == "approved"
    record.status = payload.status
    record.review_note = payload.review_note
    record.reviewed_at = datetime.utcnow()

    if payload.status == "approved" and not was_approved:
        checkin_points = get_checkin_points_for_level(
            get_active_pass_settings_by_level(db),
            record.spot.recommendation_level,
        )
        record.user.checkin_count += 1
        record.awarded_explore_points = checkin_points
        record.user.explore_points += checkin_points
    if payload.status != "approved" and was_approved and record.user.checkin_count > 0:
        record.user.checkin_count -= 1
        record.user.explore_points = max(record.user.explore_points - record.awarded_explore_points, 0)
        record.awarded_explore_points = 0

    sync_user_membership_by_points(db, record.user)
    db.add(record)
    db.commit()
    db.refresh(record)
    return checkin_to_out(record)
