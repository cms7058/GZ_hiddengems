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
from app.models.content import CommentLike, ContentMedia, SpotRecommendation, TravelNote, UserComment
from app.models.spot import ScenicSpot
from app.models.user import CheckinRecord, MiniProgramUser, ShareEvent
from app.schemas.content import ContentMediaOut, TravelNoteCreate, TravelNoteOut, UserCommentCreate, UserCommentOut
from app.schemas.growth import SpotRecommendationCreate, SpotRecommendationOut
from app.schemas.user import CheckinCreate, CheckinRecordOut, MiniProgramLoginIn, MiniProgramUserOut
from app.services.integrations import get_mini_program_service_hours
from app.services.media_storage import MediaStorageError, get_media_display_url, save_media
from app.services.memberships import sync_user_membership_by_points
from app.services.points import award_points
from app.services.safety_levels import apply_safety_level_policy
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
    return user


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


def recommendation_to_out(db: Session, item: SpotRecommendation) -> SpotRecommendationOut:
    media = db.scalars(
        select(ContentMedia).where(
            ContentMedia.owner_type == "spot_recommendation",
            ContentMedia.owner_id == item.id,
        )
    ).all()
    return SpotRecommendationOut(
        id=item.id,
        user_id=item.user_id,
        nickname=item.user.nickname,
        name_zh=item.name_zh,
        name_en=item.name_en,
        summary_zh=item.summary_zh,
        summary_en=item.summary_en,
        description_zh=item.description_zh,
        description_en=item.description_en,
        city=item.city,
        county=item.county,
        latitude=item.latitude,
        longitude=item.longitude,
        river_name=item.river_name,
        river_upstream_latitude=item.river_upstream_latitude,
        river_upstream_longitude=item.river_upstream_longitude,
        recommendation_level=item.recommendation_level,
        tag_ids=json.loads(item.tag_ids_json or "[]"),
        status=item.status,
        review_note=item.review_note,
        approved_spot_id=item.approved_spot_id,
        media=[{"id": entry.id, "media_url": entry.media_url, "media_type": entry.media_type, "display_url": get_media_display_url(db, entry.media_url)} for entry in media],
        created_at=item.created_at,
        reviewed_at=item.reviewed_at,
    )


@router.post("/login", response_model=MiniProgramUserOut)
def mini_login(payload: MiniProgramLoginIn, db: Session = Depends(get_db)) -> MiniProgramUserOut:
    openid = resolve_wechat_openid(payload.code)
    user = db.query(MiniProgramUser).filter(MiniProgramUser.openid == openid).first()
    is_new_user = user is None
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
    if is_new_user and payload.referrer_token:
        share_event = db.scalar(select(ShareEvent).where(ShareEvent.share_token == payload.referrer_token))
        if share_event is not None and share_event.user_id != user.id:
            inviter = db.get(MiniProgramUser, share_event.user_id)
            if inviter is not None and inviter.is_active:
                user.invited_by_user_id = inviter.id
                inviter.referral_registered_count += 1
                award_points(db, user=inviter, rule_code="share_registration", reference_type="share_registration", reference_id=user.id, note="分享带来新用户注册")
    apply_safety_level_policy(db, user)
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
    if not payload.image_url:
        raise HTTPException(status_code=400, detail="At least one check-in image is required")
    try:
        distance = haversine_distance_meters(float(payload.latitude), float(payload.longitude), spot.latitude, spot.longitude)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Invalid check-in location") from error
    passed = distance <= spot.checkin_radius_meters
    record = CheckinRecord(
        **payload.model_dump(),
        status="approved" if passed else "rejected",
        checkin_distance_meters=distance,
        awarded_explore_points=0,
        reviewed_at=datetime.utcnow(),
        review_note=(
            f"系统定位通过：距景点 {distance} 米，等待积分规则结算。"
            if passed
            else f"系统定位未通过：距景点 {distance} 米，打卡范围为 {spot.checkin_radius_meters} 米。"
        ),
    )
    db.add(record)
    db.flush()
    if passed:
        user.checkin_count += 1
        user.last_checkin_at = datetime.utcnow()
        record.awarded_explore_points = award_points(
            db,
            user=user,
            rule_code="checkin_success",
            reference_type="checkin",
            reference_id=record.id,
            note=f"{spot.name_zh} 打卡成功",
        )
        sync_user_membership_by_points(db, user)
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


@router.post("/comments/{comment_id}/like", response_model=UserCommentOut)
def like_comment(comment_id: int, user_id: int, db: Session = Depends(get_db)) -> UserCommentOut:
    user = ensure_active_user(db, user_id)
    ensure_user_permission(user, "can_like_comment")
    comment = db.scalar(select(UserComment).where(UserComment.id == comment_id, UserComment.status == "approved"))
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot like your own comment")
    exists = db.scalar(select(CommentLike.id).where(CommentLike.comment_id == comment_id, CommentLike.user_id == user.id))
    if exists is None:
        db.add(CommentLike(comment_id=comment_id, user_id=user.id))
        author = ensure_active_user(db, comment.user_id)
        author.like_received_count += 1
        user.like_given_count += 1
        award_points(
            db,
            user=author,
            rule_code="comment_like_received",
            reference_type="comment_like",
            reference_id=comment_id * 1_000_000 + user.id,
            note="留言获得点赞",
        )
        sync_user_membership_by_points(db, author)
        db.commit()
    db.refresh(comment)
    db.refresh(comment, attribute_names=["user", "likes"])
    return comment_to_out(comment, db, viewer_user_id=user.id)


@router.delete("/comments/{comment_id}/like", response_model=UserCommentOut)
def unlike_comment(comment_id: int, user_id: int, db: Session = Depends(get_db)) -> UserCommentOut:
    user = ensure_active_user(db, user_id)
    like = db.scalar(select(CommentLike).where(CommentLike.comment_id == comment_id, CommentLike.user_id == user.id))
    comment = db.scalar(select(UserComment).where(UserComment.id == comment_id))
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if like is not None:
        db.delete(like)
        author = db.get(MiniProgramUser, comment.user_id)
        if author is not None:
            author.like_received_count = max(0, author.like_received_count - 1)
        user.like_given_count = max(0, user.like_given_count - 1)
        db.commit()
    db.refresh(comment)
    db.refresh(comment, attribute_names=["user", "likes"])
    return comment_to_out(comment, db, viewer_user_id=user.id)


@router.post("/spot-recommendations", response_model=SpotRecommendationOut, status_code=201)
def create_spot_recommendation(payload: SpotRecommendationCreate, db: Session = Depends(get_db)) -> SpotRecommendationOut:
    user = ensure_active_user(db, payload.user_id)
    ensure_user_permission(user, "can_recommend_spot")
    if (payload.latitude is None) != (payload.longitude is None):
        raise HTTPException(status_code=400, detail="Both latitude and longitude must be provided together")
    item = SpotRecommendation(
        **payload.model_dump(exclude={"tag_ids", "media"}),
        tag_ids_json=json.dumps(payload.tag_ids),
        status="pending",
    )
    db.add(item)
    db.flush()
    for media in payload.media:
        url = str(media.get("media_url") or "")
        media_type = str(media.get("media_type") or "image")
        if url and media_type in {"image", "video"}:
            db.add(ContentMedia(owner_type="spot_recommendation", owner_id=item.id, media_url=url, media_type=media_type, status="pending"))
    db.commit()
    db.refresh(item)
    db.refresh(item, attribute_names=["user"])
    return recommendation_to_out(db, item)


@router.post("/shares")
def record_share(user_id: int, db: Session = Depends(get_db)) -> dict:
    import secrets

    user = ensure_active_user(db, user_id)
    ensure_user_permission(user, "can_share")
    token = secrets.token_urlsafe(18)
    event = ShareEvent(user_id=user.id, share_token=token)
    db.add(event)
    db.flush()
    user.share_count += 1
    awarded = award_points(db, user=user, rule_code="share", reference_type="share", reference_id=event.id, note="发起小程序分享")
    sync_user_membership_by_points(db, user)
    db.commit()
    return {"share_token": token, "awarded_points": awarded}
