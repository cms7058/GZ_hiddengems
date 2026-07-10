from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.content import TravelNote, UserComment
from app.models.spot import ScenicSpot
from app.models.user import CheckinRecord, MiniProgramUser
from app.schemas.content import TravelNoteCreate, TravelNoteOut, UserCommentCreate, UserCommentOut
from app.schemas.user import CheckinCreate, CheckinRecordOut
from app.services.integrations import get_mini_program_service_hours
from app.services.spot_mapper import comment_to_out, travel_note_to_out


router = APIRouter()

UPLOAD_BASE = Path(__file__).resolve().parents[3] / "static" / "uploads"
ALLOWED_MEDIA_SUFFIXES = {
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
    ".gif": "image",
    ".mp4": "video",
    ".mov": "video",
    ".m4v": "video",
}


@router.get("/service-hours")
def get_service_hours(db: Session = Depends(get_db)) -> dict:
    return get_mini_program_service_hours(db)


def ensure_active_user(db: Session, user_id: int) -> MiniProgramUser:
    user = db.get(MiniProgramUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def ensure_active_spot(db: Session, spot_id: int) -> ScenicSpot:
    spot = db.get(ScenicSpot, spot_id)
    if spot is None or not spot.is_active or spot.review_status != "approved":
        raise HTTPException(status_code=404, detail="Spot not found")
    return spot


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
    )


@router.post("/uploads")
async def upload_mini_media(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    media_type = ALLOWED_MEDIA_SUFFIXES.get(suffix)
    if media_type is None:
        raise HTTPException(status_code=400, detail="Unsupported media type")

    upload_root = UPLOAD_BASE / "mini-shares"
    upload_root.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    target = upload_root / filename
    content = await file.read()
    target.write_bytes(content)
    media_url = f"/media/mini-shares/{filename}"
    return {
        "media_url": media_url,
        "media_type": media_type,
        "image_url": media_url if media_type == "image" else None,
    }


@router.post("/checkins", response_model=CheckinRecordOut, status_code=201)
def create_checkin(payload: CheckinCreate, db: Session = Depends(get_db)) -> CheckinRecordOut:
    ensure_active_user(db, payload.user_id)
    ensure_active_spot(db, payload.spot_id)
    record = CheckinRecord(**payload.model_dump(), status="pending")
    db.add(record)
    db.commit()
    db.refresh(record)
    db.refresh(record, attribute_names=["user", "spot"])
    return checkin_to_out(record)


@router.post("/travel-notes", response_model=TravelNoteOut, status_code=201)
def create_travel_note(payload: TravelNoteCreate, db: Session = Depends(get_db)) -> TravelNoteOut:
    ensure_active_user(db, payload.user_id)
    ensure_active_spot(db, payload.spot_id)
    note = TravelNote(**payload.model_dump(exclude={"status", "is_featured"}), status="pending", is_featured=False)
    db.add(note)
    db.commit()
    db.refresh(note)
    db.refresh(note, attribute_names=["user", "spot"])
    return travel_note_to_out(note)


@router.post("/comments", response_model=UserCommentOut, status_code=201)
def create_comment(payload: UserCommentCreate, db: Session = Depends(get_db)) -> UserCommentOut:
    ensure_active_user(db, payload.user_id)
    ensure_active_spot(db, payload.spot_id)
    comment = UserComment(**payload.model_dump(exclude={"status"}), status="pending")
    db.add(comment)
    db.commit()
    db.refresh(comment)
    db.refresh(comment, attribute_names=["user", "spot"])
    return comment_to_out(comment)
