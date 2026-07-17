from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
from urllib.request import urlopen
import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.content import ContentMedia, TravelNote, UserComment
from app.models.spot import ScenicSpot
from app.models.user import CheckinRecord, MiniProgramUser
from app.schemas.content import ContentMediaOut, TravelNoteCreate, TravelNoteOut, UserCommentCreate, UserCommentOut
from app.schemas.user import CheckinCreate, CheckinRecordOut, MiniProgramLoginIn, MiniProgramUserOut
from app.services.integrations import get_mini_program_service_hours
from app.services.media_storage import MediaStorageError, get_media_display_url, save_media
from app.services.memberships import sync_user_membership_by_points
from app.services.pass_levels import get_active_pass_settings_by_level, get_checkin_points_for_level
from app.services.spot_mapper import comment_to_out, travel_note_to_out


router = APIRouter()

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
MAX_IMAGE_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_VIDEO_UPLOAD_BYTES = 8 * 1024 * 1024


def user_to_out(db: Session, user: MiniProgramUser) -> MiniProgramUserOut:
    result = MiniProgramUserOut.model_validate(user)
    return result.model_copy(update={"avatar_url": get_media_display_url(db, user.avatar_url)})


@router.get("/service-hours")
def get_service_hours(db: Session = Depends(get_db)) -> dict:
    return get_mini_program_service_hours(db)


def ensure_active_user(db: Session, user_id: int) -> MiniProgramUser:
    user = db.get(MiniProgramUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_out(db, user)


def ensure_user_permission(user: MiniProgramUser, permission: str) -> None:
    if not getattr(user, permission, False):
        raise HTTPException(status_code=403, detail="User permission denied")


def ensure_successful_checkin(db: Session, user_id: int, spot_id: int) -> None:
    has_successful_checkin = db.scalar(
        select(CheckinRecord.id).where(
            CheckinRecord.user_id == user_id,
            CheckinRecord.spot_id == spot_id,
            CheckinRecord.status == "approved",
        )
    )
    if has_successful_checkin is None:
        raise HTTPException(status_code=403, detail="Successful check-in is required before publishing notes or comments")


def resolve_wechat_openid(code: str) -> str:
    if not settings.wechat_mini_appid or not settings.wechat_mini_secret:
        return "dev-openid"

    query = urlencode(
        {
            "appid": settings.wechat_mini_appid,
            "secret": settings.wechat_mini_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    try:
        with urlopen(f"https://api.weixin.qq.com/sns/jscode2session?{query}", timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"WeChat login failed: {error}") from error

    if data.get("errcode"):
        message = data.get("errmsg") or "WeChat login failed"
        raise HTTPException(
            status_code=400,
            detail=f"WeChat login failed: {message}. Verify WECHAT_MINI_APPID and WECHAT_MINI_SECRET match the current mini program.",
        )
    openid = data.get("openid")
    if not openid:
        raise HTTPException(status_code=400, detail="WeChat openid missing")
    return openid


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
        awarded_explore_points=record.awarded_explore_points,
        promoted_spot_image_id=record.promoted_spot_image_id,
        checkin_distance_meters=record.checkin_distance_meters,
        created_at=record.created_at,
        reviewed_at=record.reviewed_at,
    )


def haversine_distance_meters(latitude: float, longitude: float, target_latitude: float, target_longitude: float) -> int:
    from math import asin, cos, radians, sin, sqrt

    earth_radius = 6371000
    latitude_delta = radians(target_latitude - latitude)
    longitude_delta = radians(target_longitude - longitude)
    a = sin(latitude_delta / 2) ** 2 + cos(radians(latitude)) * cos(radians(target_latitude)) * sin(longitude_delta / 2) ** 2
    return round(earth_radius * 2 * asin(sqrt(a)))


def add_content_media(db: Session, owner_type: str, owner_id: int, media) -> None:
    for item in media:
        db.add(
            ContentMedia(
                owner_type=owner_type,
                owner_id=owner_id,
                media_url=item.media_url,
                media_type=item.media_type,
                status="pending",
            )
        )


@router.post("/login", response_model=MiniProgramUserOut)
def mini_login(payload: MiniProgramLoginIn, db: Session = Depends(get_db)) -> MiniProgramUserOut:
    openid = resolve_wechat_openid(payload.code)
    user = db.query(MiniProgramUser).filter(MiniProgramUser.openid == openid).first()
    if user is None:
        user = MiniProgramUser(
            openid=openid,
            nickname=payload.nickname or "秘境探索者",
            avatar_url=payload.avatar_url,
            language=payload.language or "zh-CN",
        )
    else:
        user.is_active = True
        if payload.nickname:
            user.nickname = payload.nickname
        if payload.avatar_url:
            user.avatar_url = payload.avatar_url
        if payload.language:
            user.language = payload.language
    db.add(user)
    db.flush()
    sync_user_membership_by_points(db, user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/uploads")
async def upload_mini_media(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    media_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> dict:
    user = ensure_active_user(db, user_id)
    suffix = Path(file.filename or "").suffix.lower()
    requested_media_type = (media_type or "").strip().lower()
    detected_media_type = ALLOWED_MEDIA_SUFFIXES.get(suffix)
    resolved_media_type = detected_media_type or requested_media_type
    if resolved_media_type not in {"image", "video"}:
        raise HTTPException(status_code=400, detail="Unsupported media type")
    if not detected_media_type:
        suffix = ".mp4" if resolved_media_type == "video" else ".jpg"
    ensure_user_permission(user, "can_upload_video" if resolved_media_type == "video" else "can_upload_image")

    content = await file.read()
    max_bytes = MAX_VIDEO_UPLOAD_BYTES if resolved_media_type == "video" else MAX_IMAGE_UPLOAD_BYTES
    if len(content) > max_bytes:
        limit = "8 MB" if resolved_media_type == "video" else "2 MB"
        raise HTTPException(status_code=400, detail=f"{resolved_media_type.capitalize()} must not exceed {limit}")
    try:
        media_url = await run_in_threadpool(save_media, db, "mini-shares", suffix, content, file.content_type)
    except MediaStorageError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {
        "media_url": media_url,
        "media_type": resolved_media_type,
        "image_url": media_url if resolved_media_type == "image" else None,
    }


@router.post("/checkins", response_model=CheckinRecordOut, status_code=201)
def create_checkin(payload: CheckinCreate, db: Session = Depends(get_db)) -> CheckinRecordOut:
    user = ensure_active_user(db, payload.user_id)
    ensure_user_permission(user, "can_checkin")
    spot = ensure_active_spot(db, payload.spot_id)
    if payload.latitude is None or payload.longitude is None:
        raise HTTPException(status_code=400, detail="Location is required for check-in")
    try:
        distance = haversine_distance_meters(float(payload.latitude), float(payload.longitude), spot.latitude, spot.longitude)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Invalid check-in location") from error
    passed = distance <= spot.checkin_radius_meters
    awarded_points = 0
    if passed:
        awarded_points = get_checkin_points_for_level(
            get_active_pass_settings_by_level(db), spot.recommendation_level
        )
        user.checkin_count += 1
        user.explore_points += awarded_points
        sync_user_membership_by_points(db, user)
    record = CheckinRecord(
        **payload.model_dump(),
        status="approved" if passed else "rejected",
        checkin_distance_meters=distance,
        awarded_explore_points=awarded_points,
        reviewed_at=datetime.utcnow(),
        review_note=(
            f"系统定位通过：距景点 {distance} 米，已获得 {awarded_points} 探秘积分。"
            if passed
            else f"系统定位未通过：距景点 {distance} 米，打卡范围为 {spot.checkin_radius_meters} 米。"
        ),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    db.refresh(record, attribute_names=["user", "spot"])
    return checkin_to_out(record)


@router.post("/travel-notes", response_model=TravelNoteOut, status_code=201)
def create_travel_note(payload: TravelNoteCreate, db: Session = Depends(get_db)) -> TravelNoteOut:
    user = ensure_active_user(db, payload.user_id)
    ensure_user_permission(user, "can_comment")
    ensure_active_spot(db, payload.spot_id)
    ensure_successful_checkin(db, payload.user_id, payload.spot_id)
    note = TravelNote(**payload.model_dump(exclude={"status", "is_featured", "media"}), status="pending", is_featured=False)
    db.add(note)
    db.flush()
    add_content_media(db, "travel_note", note.id, payload.media)
    db.commit()
    db.refresh(note)
    db.refresh(note, attribute_names=["user", "spot"])
    return travel_note_to_out(note, db)


@router.post("/comments", response_model=UserCommentOut, status_code=201)
def create_comment(payload: UserCommentCreate, db: Session = Depends(get_db)) -> UserCommentOut:
    user = ensure_active_user(db, payload.user_id)
    ensure_user_permission(user, "can_comment")
    ensure_active_spot(db, payload.spot_id)
    ensure_successful_checkin(db, payload.user_id, payload.spot_id)
    comment = UserComment(**payload.model_dump(exclude={"status", "media"}), status="pending")
    db.add(comment)
    db.flush()
    add_content_media(db, "comment", comment.id, payload.media)
    db.commit()
    db.refresh(comment)
    db.refresh(comment, attribute_names=["user", "spot"])
    return comment_to_out(comment, db)
