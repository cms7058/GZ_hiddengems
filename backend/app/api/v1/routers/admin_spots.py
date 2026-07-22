import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.content import LifestyleRecommendation, SpotImage, TravelNote, UserComment
from app.models.spot import ScenicSpot, SpotChildPoint, Tag, WechatChannelVideo
from app.models.user import CheckinRecord, PassLevelSetting
from app.schemas.spot import (
    ReviewStatusUpdate,
    SpotAdminOut,
    SpotChildPointCreate,
    SpotChildPointOut,
    SpotChildPointUpdate,
    SpotCreate,
    SpotUpdate,
)
from app.schemas.pagination import Page
from app.schemas.user import CheckinRecordOut
from app.services.pagination import build_page, paginated_scalars
from app.services.media_storage import MediaStorageError, cache_remote_image, delete_media
from app.services.coordinates import normalize_to_gcj02
from app.services.spot_mapper import spot_to_admin_out
from app.services.spot_codes import assign_spot_code


router = APIRouter()


def checkin_to_admin_out(record: CheckinRecord) -> CheckinRecordOut:
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
        route_distance_meters=record.route_distance_meters,
        route_duration_seconds=record.route_duration_seconds,
        elapsed_seconds=record.elapsed_seconds,
        travel_time_ratio=record.travel_time_ratio,
        risk_status=record.risk_status,
        risk_reason=record.risk_reason,
        previous_checkin_id=record.previous_checkin_id,
    )


def load_tags(db: Session, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    tags = db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all()
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=400, detail="One or more tags do not exist")
    return tags


def validate_pass_level(db: Session, level: int) -> None:
    setting = db.scalar(select(PassLevelSetting).where(PassLevelSetting.level == level))
    if setting is None:
        raise HTTPException(status_code=400, detail="Selected pass level does not exist")


def normalize_spot_coordinates(
    data: dict,
    fallback_latitude: Optional[float] = None,
    fallback_longitude: Optional[float] = None,
) -> None:
    source = data.pop("coordinate_system", "gcj02") or "gcj02"
    latitude = data.get("latitude", fallback_latitude)
    longitude = data.get("longitude", fallback_longitude)
    if latitude is None or longitude is None:
        return
    try:
        data["latitude"], data["longitude"] = normalize_to_gcj02(float(latitude), float(longitude), source)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def prepare_wechat_channel_videos(db: Session, videos: list[dict]) -> list[dict]:
    records: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()
    for video in videos:
        data = dict(video)
        key = (data["finder_user_name"], data["feed_id"])
        if key in seen_keys:
            raise HTTPException(status_code=400, detail="Duplicate Video Channel user ID and video ID")
        seen_keys.add(key)
        try:
            data["cover_url"] = cache_remote_image(db, data["cover_url"])
        except MediaStorageError as error:
            raise HTTPException(status_code=400, detail=f"Video Channel cover could not be cached: {error}") from error
        records.append(data)
    return records


def build_wechat_channel_videos(db: Session, videos: list[dict]) -> list[WechatChannelVideo]:
    return [WechatChannelVideo(**data) for data in prepare_wechat_channel_videos(db, videos)]


def sync_wechat_channel_videos(db: Session, spot: ScenicSpot, videos: list[dict]) -> None:
    """Update channel videos in place to preserve their unique spot/user/video key."""
    prepared = prepare_wechat_channel_videos(db, videos)
    existing_by_key = {
        (video.finder_user_name, video.feed_id): video
        for video in spot.wechat_channel_videos
    }
    incoming_keys = set()
    for data in prepared:
        key = (data["finder_user_name"], data["feed_id"])
        incoming_keys.add(key)
        existing = existing_by_key.get(key)
        if existing is None:
            spot.wechat_channel_videos.append(WechatChannelVideo(**data))
            continue
        for field, value in data.items():
            setattr(existing, field, value)
    for key, existing in existing_by_key.items():
        if key not in incoming_keys:
            db.delete(existing)


@router.get("", response_model=Page[SpotAdminOut])
def list_admin_spots(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    name: Optional[str] = Query(default=None, max_length=128),
    has_image: Optional[bool] = Query(default=None),
    tag_id: Optional[int] = Query(default=None, ge=1),
    recommendation_level: Optional[int] = Query(default=None, ge=0),
    required_points_min: Optional[int] = Query(default=None, ge=0),
    required_points_max: Optional[int] = Query(default=None, ge=0),
    review_status: Optional[str] = Query(default=None, max_length=32),
    is_active: Optional[bool] = Query(default=None),
    sort_by: str = Query(default="id", pattern="^(id|spot_code|name|recommendation_level|required_explore_points|review_status|is_active|has_image)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[SpotAdminOut]:
    statement = select(ScenicSpot).options(
        selectinload(ScenicSpot.tags),
        selectinload(ScenicSpot.child_points),
        selectinload(ScenicSpot.spot_images),
        selectinload(ScenicSpot.wechat_channel_videos),
    )
    active_image = ScenicSpot.spot_images.any(
        and_(SpotImage.is_active.is_(True), SpotImage.media_type == "image")
    )
    if name and name.strip():
        keyword = f"%{name.strip()}%"
        statement = statement.where((ScenicSpot.name_zh.ilike(keyword)) | (ScenicSpot.name_en.ilike(keyword)))
    if has_image is not None:
        statement = statement.where(active_image if has_image else ~active_image)
    if tag_id is not None:
        statement = statement.where(ScenicSpot.tags.any(Tag.id == tag_id))
    if recommendation_level is not None:
        statement = statement.where(ScenicSpot.recommendation_level == recommendation_level)
    if required_points_min is not None:
        statement = statement.where(ScenicSpot.required_explore_points >= required_points_min)
    if required_points_max is not None:
        statement = statement.where(ScenicSpot.required_explore_points <= required_points_max)
    if review_status:
        statement = statement.where(ScenicSpot.review_status == review_status)
    if is_active is not None:
        statement = statement.where(ScenicSpot.is_active.is_(is_active))

    sort_columns = {
        "id": ScenicSpot.id,
        "spot_code": ScenicSpot.spot_code,
        "name": ScenicSpot.name_zh,
        "recommendation_level": ScenicSpot.recommendation_level,
        "required_explore_points": ScenicSpot.required_explore_points,
        "review_status": ScenicSpot.review_status,
        "is_active": ScenicSpot.is_active,
        "has_image": active_image,
    }
    order_column = sort_columns[sort_by]
    statement = statement.order_by(order_column.asc() if sort_order == "asc" else order_column.desc(), ScenicSpot.id.desc())
    result = paginated_scalars(db, statement, page, page_size)
    return build_page(
        [spot_to_admin_out(spot, db) for spot in result.items],
        result.total,
        result.page,
        result.page_size,
    )


@router.post("", response_model=SpotAdminOut, status_code=201)
def create_admin_spot(
    payload: SpotCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SpotAdminOut:
    tags = load_tags(db, payload.tag_ids)
    validate_pass_level(db, payload.recommendation_level)
    data = payload.model_dump(exclude={"tag_ids", "video_channel_urls", "wechat_channel_videos"})
    data["video_channel_urls_json"] = json.dumps(payload.video_channel_urls, ensure_ascii=False)
    normalize_spot_coordinates(data)
    spot = ScenicSpot(**data)
    spot.spot_code = assign_spot_code(db, spot.recommendation_level)
    spot.tags = tags
    spot.wechat_channel_videos = build_wechat_channel_videos(db, [video.model_dump() for video in payload.wechat_channel_videos])

    db.add(spot)
    db.commit()
    db.refresh(spot)
    db.refresh(spot, attribute_names=["tags"])
    return spot_to_admin_out(spot, db)


@router.get("/{spot_id}", response_model=SpotAdminOut)
def get_admin_spot(
    spot_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SpotAdminOut:
    spot = db.scalar(
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags), selectinload(ScenicSpot.child_points), selectinload(ScenicSpot.spot_images), selectinload(ScenicSpot.wechat_channel_videos))
        .where(ScenicSpot.id == spot_id)
    )
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")
    return spot_to_admin_out(spot, db)


@router.get("/{spot_id}/checkins", response_model=Page[CheckinRecordOut])
def list_spot_checkins(
    spot_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[CheckinRecordOut]:
    if db.get(ScenicSpot, spot_id) is None:
        raise HTTPException(status_code=404, detail="Spot not found")
    result = paginated_scalars(
        db,
        select(CheckinRecord)
        .options(joinedload(CheckinRecord.user), joinedload(CheckinRecord.spot))
        .where(CheckinRecord.spot_id == spot_id)
        .order_by(CheckinRecord.id.desc()),
        page,
        page_size,
    )
    return build_page(
        [checkin_to_admin_out(record) for record in result.items],
        result.total,
        result.page,
        result.page_size,
    )


@router.patch("/{spot_id}", response_model=SpotAdminOut)
def update_admin_spot(
    spot_id: int,
    payload: SpotUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SpotAdminOut:
    spot = db.scalar(
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags), selectinload(ScenicSpot.child_points), selectinload(ScenicSpot.spot_images), selectinload(ScenicSpot.wechat_channel_videos))
        .where(ScenicSpot.id == spot_id)
    )
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")

    update_data = payload.model_dump(exclude_unset=True)
    tag_ids = update_data.pop("tag_ids", None)
    wechat_channel_videos = update_data.pop("wechat_channel_videos", None)
    video_channel_urls = update_data.pop("video_channel_urls", None)
    if video_channel_urls is not None:
        update_data["video_channel_urls_json"] = json.dumps(video_channel_urls, ensure_ascii=False)
    normalize_spot_coordinates(update_data, spot.latitude, spot.longitude)
    if "recommendation_level" in update_data:
        validate_pass_level(db, update_data["recommendation_level"])
        if update_data["recommendation_level"] != spot.recommendation_level:
            spot.spot_code = assign_spot_code(db, update_data["recommendation_level"], exclude_spot_id=spot.id)
    for field, value in update_data.items():
        setattr(spot, field, value)
    if tag_ids is not None:
        spot.tags = load_tags(db, tag_ids)
    if wechat_channel_videos is not None:
        sync_wechat_channel_videos(db, spot, wechat_channel_videos)

    db.add(spot)
    db.commit()
    db.refresh(spot)
    db.refresh(spot, attribute_names=["tags"])
    return spot_to_admin_out(spot, db)


@router.patch("/{spot_id}/review", response_model=SpotAdminOut)
def review_admin_spot(
    spot_id: int,
    payload: ReviewStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SpotAdminOut:
    spot = db.scalar(
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags), selectinload(ScenicSpot.child_points), selectinload(ScenicSpot.spot_images), selectinload(ScenicSpot.wechat_channel_videos))
        .where(ScenicSpot.id == spot_id)
    )
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")

    spot.review_status = payload.review_status
    db.add(spot)
    db.commit()
    db.refresh(spot)
    db.refresh(spot, attribute_names=["tags"])
    return spot_to_admin_out(spot, db)


@router.post("/{spot_id}/child-points", response_model=SpotChildPointOut, status_code=201)
def create_spot_child_point(
    spot_id: int,
    payload: SpotChildPointCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SpotChildPointOut:
    spot = db.get(ScenicSpot, spot_id)
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")
    data = payload.model_dump()
    normalize_spot_coordinates(data)
    point = SpotChildPoint(spot_id=spot_id, **data)
    db.add(point)
    db.commit()
    db.refresh(point)
    return SpotChildPointOut.model_validate(point)


@router.patch("/{spot_id}/child-points/{point_id}", response_model=SpotChildPointOut)
def update_spot_child_point(
    spot_id: int,
    point_id: int,
    payload: SpotChildPointUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SpotChildPointOut:
    point = db.scalar(
        select(SpotChildPoint).where(
            SpotChildPoint.id == point_id,
            SpotChildPoint.spot_id == spot_id,
        )
    )
    if point is None:
        raise HTTPException(status_code=404, detail="Child point not found")
    update_data = payload.model_dump(exclude_unset=True)
    normalize_spot_coordinates(update_data, point.latitude, point.longitude)
    for field, value in update_data.items():
        setattr(point, field, value)
    db.add(point)
    db.commit()
    db.refresh(point)
    return SpotChildPointOut.model_validate(point)


@router.delete("/{spot_id}/child-points/{point_id}", status_code=204)
def delete_spot_child_point(
    spot_id: int,
    point_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    point = db.scalar(
        select(SpotChildPoint).where(
            SpotChildPoint.id == point_id,
            SpotChildPoint.spot_id == spot_id,
        )
    )
    if point is None:
        raise HTTPException(status_code=404, detail="Child point not found")
    point.is_active = False
    db.add(point)
    db.commit()


@router.delete("/{spot_id}", status_code=204)
def delete_admin_spot(
    spot_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    spot = db.scalar(
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags))
        .where(ScenicSpot.id == spot_id)
    )
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")

    images = db.scalars(select(SpotImage).where(SpotImage.spot_id == spot_id)).all()
    notes = db.scalars(select(TravelNote).where(TravelNote.spot_id == spot_id)).all()
    comments = db.scalars(select(UserComment).where(UserComment.spot_id == spot_id)).all()
    recommendations = db.scalars(select(LifestyleRecommendation).where(LifestyleRecommendation.spot_id == spot_id)).all()
    checkins = db.scalars(select(CheckinRecord).where(CheckinRecord.spot_id == spot_id)).all()
    media_urls = {
        url
        for url in [
            *(image.image_url for image in images),
            *(note.image_url for note in notes),
            *(comment.image_url for comment in comments),
            *(item.image_url for item in recommendations),
            *(record.image_url for record in checkins),
            *(record.media_url for record in checkins),
        ]
        if url
    }
    try:
        for media_url in media_urls:
            delete_media(db, media_url)
    except MediaStorageError as error:
        raise HTTPException(status_code=502, detail=f"Could not delete associated media: {error}") from error

    for record in [*images, *notes, *comments, *recommendations, *checkins]:
        db.delete(record)
    spot.tags.clear()
    db.delete(spot)
    db.commit()
