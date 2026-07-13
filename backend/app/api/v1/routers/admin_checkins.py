from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.content import SpotImage
from app.models.user import CheckinRecord
from app.schemas.pagination import Page
from app.schemas.user import CheckinRecordOut, CheckinReviewUpdate
from app.services.pagination import build_page, paginated_scalars
from app.services.memberships import sync_user_membership_by_points
from app.services.pass_levels import get_active_pass_settings_by_level, get_checkin_points_for_level
from app.services.media_storage import MediaStorageError, delete_media


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
        media_url=record.media_url,
        media_type=record.media_type,
        note=record.note,
        review_note=record.review_note,
        awarded_explore_points=record.awarded_explore_points,
        promoted_spot_image_id=record.promoted_spot_image_id,
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
    media_url = record.media_url or record.image_url
    if media_url:
        promoted_image = db.get(SpotImage, record.promoted_spot_image_id) if record.promoted_spot_image_id else None
        if payload.status == "approved":
            if promoted_image is None:
                promoted_image = SpotImage(
                    spot_id=record.spot_id,
                    image_url=media_url,
                    media_type=record.media_type or "image",
                    caption=f"用户打卡：{record.user.nickname}",
                    sort_order=999,
                    is_cover=False,
                    is_active=True,
                )
                db.add(promoted_image)
                db.flush()
                record.promoted_spot_image_id = promoted_image.id
            else:
                promoted_image.is_active = True
                db.add(promoted_image)
        elif promoted_image is not None:
            promoted_image.is_active = False
            db.add(promoted_image)
    if payload.status != "approved" and was_approved and record.user.checkin_count > 0:
        record.user.checkin_count -= 1
        record.user.explore_points = max(record.user.explore_points - record.awarded_explore_points, 0)
        record.awarded_explore_points = 0

    sync_user_membership_by_points(db, record.user)
    db.add(record)
    db.commit()
    db.refresh(record)
    return checkin_to_out(record)


@router.delete("/{checkin_id}", status_code=204)
def delete_checkin(
    checkin_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    record = db.scalar(
        select(CheckinRecord)
        .options(joinedload(CheckinRecord.promoted_spot_image), joinedload(CheckinRecord.user))
        .where(CheckinRecord.id == checkin_id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Checkin record not found")
    media_urls = {url for url in (record.image_url, record.media_url) if url}
    if record.promoted_spot_image is not None:
        record.promoted_spot_image_id = None
        db.add(record)
        db.flush()
        db.delete(record.promoted_spot_image)
    try:
        for media_url in media_urls:
            delete_media(db, media_url)
    except MediaStorageError as error:
        raise HTTPException(status_code=502, detail=f"Could not delete check-in media: {error}") from error
    if record.status == "approved":
        record.user.checkin_count = max(record.user.checkin_count - 1, 0)
        record.user.explore_points = max(record.user.explore_points - record.awarded_explore_points, 0)
        sync_user_membership_by_points(db, record.user)
    db.delete(record)
    db.commit()
