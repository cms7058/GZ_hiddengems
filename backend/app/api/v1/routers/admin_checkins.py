from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.user import CheckinRecord
from app.schemas.user import CheckinRecordOut, CheckinReviewUpdate


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
    )


@router.get("", response_model=list[CheckinRecordOut])
def list_checkins(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[CheckinRecordOut]:
    records = db.scalars(
        select(CheckinRecord)
        .options(joinedload(CheckinRecord.user), joinedload(CheckinRecord.spot))
        .order_by(CheckinRecord.id.desc())
    ).all()
    return [checkin_to_out(record) for record in records]


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
        record.user.checkin_count += 1
    if payload.status != "approved" and was_approved and record.user.checkin_count > 0:
        record.user.checkin_count -= 1

    db.add(record)
    db.commit()
    db.refresh(record)
    return checkin_to_out(record)
