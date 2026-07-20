from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.session import get_db
from app.models.content import LifestyleRecommendation, SpotImage, TravelNote, UserComment
from app.models.spot import ScenicSpot, Tag
from app.models.user import CheckinRecord, MiniProgramUser
from app.schemas.spot import HomeSpotOut, LockedNearbySpotCountOut, LockedSpotDetailOut, LockedSpotPreviewOut, MapSpotOut, SpotDetailOut
from app.services.geo import distance_km_between
from app.services.pass_levels import get_active_pass_settings_by_level, get_marker_colors_by_level, get_spot_unlock_state
from app.services.spot_mapper import spot_to_detail_out, spot_to_home_out, spot_to_locked_detail_out, spot_to_locked_preview_out, spot_to_map_out


router = APIRouter()


def resolve_user_context(
    db: Session,
    user_id: Optional[int] = None,
    explore_points: int = 0,
) -> tuple[Optional[MiniProgramUser], int]:
    if user_id is None:
        return None, explore_points
    user = db.get(MiniProgramUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    return user, user.explore_points


def find_locked_spots_nearby(
    db: Session,
    *,
    user: MiniProgramUser,
    user_explore_points: int,
    latitude: float,
    longitude: float,
    radius_km: float,
    tag_ids: Optional[list[int]] = None,
    level_ids: Optional[list[int]] = None,
) -> list[tuple[ScenicSpot, int, float]]:
    statement = (
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags), selectinload(ScenicSpot.spot_images), selectinload(ScenicSpot.wechat_channel_videos))
        .where(
            ScenicSpot.is_active.is_(True),
            ScenicSpot.review_status == "approved",
        )
    )
    if tag_ids:
        statement = statement.join(ScenicSpot.tags).where(Tag.id.in_(tag_ids)).distinct()
    if level_ids:
        statement = statement.where(ScenicSpot.recommendation_level.in_(level_ids))
    pass_settings_by_level = get_active_pass_settings_by_level(db)
    nearby_spots = []
    for spot in db.scalars(statement).all():
        is_unlocked, required_explore_points = get_spot_unlock_state(
            spot_required_explore_points=spot.required_explore_points,
            recommendation_level=spot.recommendation_level,
            user=user,
            fallback_explore_points=user_explore_points,
            settings_by_level=pass_settings_by_level,
        )
        if is_unlocked:
            continue
        distance_km = distance_km_between(latitude, longitude, spot.latitude, spot.longitude)
        if distance_km <= radius_km:
            nearby_spots.append((spot, required_explore_points, distance_km))
    return sorted(nearby_spots, key=lambda item: (item[2], item[1], item[0].id))


@router.get("/map", response_model=list[MapSpotOut])
def list_map_spots(
    lang: str = Query(default="zh-CN"),
    tag_ids: list[int] = Query(default=[]),
    user_level: int = Query(default=0, ge=0, le=99),
    is_member: bool = Query(default=False),
    user_id: Optional[int] = Query(default=None),
    explore_points: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[MapSpotOut]:
    user, user_explore_points = resolve_user_context(db, user_id, explore_points)
    statement = (
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags), selectinload(ScenicSpot.spot_images), selectinload(ScenicSpot.wechat_channel_videos))
        .where(
            ScenicSpot.is_active.is_(True),
            ScenicSpot.review_status == "approved",
        )
        .order_by(ScenicSpot.recommendation_level.desc(), ScenicSpot.id.desc())
    )
    if tag_ids:
        statement = statement.join(ScenicSpot.tags).where(Tag.id.in_(tag_ids)).distinct()

    spots = db.scalars(statement).all()
    marker_colors_by_level = get_marker_colors_by_level(db)
    pass_settings_by_level = get_active_pass_settings_by_level(db)
    map_spots = [
        spot_to_map_out(
            spot,
            lang=lang,
            user_level=user_level,
            is_member=is_member,
            user_explore_points=user_explore_points,
            marker_colors_by_level=marker_colors_by_level,
            pass_settings_by_level=pass_settings_by_level,
            user=user,
            db=db,
        )
        for spot in spots
    ]
    return [spot for spot in map_spots if spot.is_unlocked]


@router.get("/locked-nearby", response_model=list[LockedSpotPreviewOut])
def list_locked_spots_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=20, ge=0, le=20000),
    lang: str = Query(default="zh-CN"),
    user_id: int = Query(..., ge=1),
    tag_ids: list[int] = Query(default=[]),
    level_ids: list[int] = Query(default=[]),
    db: Session = Depends(get_db),
) -> list[LockedSpotPreviewOut]:
    """List locked nearby spots without exposing their coordinates to the client."""
    user, user_explore_points = resolve_user_context(db, user_id)
    marker_colors_by_level = get_marker_colors_by_level(db)
    previews = []
    for spot, required_explore_points, distance_km in find_locked_spots_nearby(
        db,
        user=user,
        user_explore_points=user_explore_points,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        tag_ids=tag_ids,
        level_ids=level_ids,
    ):
        previews.append(
            spot_to_locked_preview_out(
                spot,
                lang=lang,
                user_explore_points=user_explore_points,
                required_explore_points=required_explore_points,
                distance_km=distance_km,
                marker_colors_by_level=marker_colors_by_level,
                db=db,
            )
        )
    return previews


@router.get("/home-catalog", response_model=list[HomeSpotOut])
def list_home_catalog(
    lang: str = Query(default="zh-CN"),
    tag_ids: list[int] = Query(default=[]),
    level_ids: list[int] = Query(default=[]),
    user_id: Optional[int] = Query(default=None),
    explore_points: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[HomeSpotOut]:
    user, user_explore_points = resolve_user_context(db, user_id, explore_points)
    statement = (
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags))
        .where(ScenicSpot.is_active.is_(True), ScenicSpot.review_status == "approved")
        .order_by(ScenicSpot.recommendation_level.asc(), ScenicSpot.id.asc())
    )
    if tag_ids:
        statement = statement.join(ScenicSpot.tags).where(Tag.id.in_(tag_ids)).distinct()
    if level_ids:
        statement = statement.where(ScenicSpot.recommendation_level.in_(level_ids))
    marker_colors = get_marker_colors_by_level(db)
    pass_settings = get_active_pass_settings_by_level(db)
    return [
        spot_to_home_out(
            spot,
            lang=lang,
            user=user,
            user_explore_points=user_explore_points,
            marker_colors_by_level=marker_colors,
            pass_settings_by_level=pass_settings,
        )
        for spot in db.scalars(statement).all()
    ]


@router.get("/locked-nearby/count", response_model=LockedNearbySpotCountOut)
def count_locked_spots_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=20, ge=0, le=20000),
    user_id: int = Query(..., ge=1),
    tag_ids: list[int] = Query(default=[]),
    level_ids: list[int] = Query(default=[]),
    db: Session = Depends(get_db),
) -> LockedNearbySpotCountOut:
    user, user_explore_points = resolve_user_context(db, user_id)
    spots = find_locked_spots_nearby(
        db,
        user=user,
        user_explore_points=user_explore_points,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        tag_ids=tag_ids,
        level_ids=level_ids,
    )
    return LockedNearbySpotCountOut(count=len(spots))


@router.get("/locked-preview/{spot_id}", response_model=LockedSpotDetailOut)
def get_locked_spot_preview(
    spot_id: int,
    lang: str = Query(default="zh-CN"),
    user_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> LockedSpotDetailOut:
    user, user_explore_points = resolve_user_context(db, user_id)
    spot = db.scalar(
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags), selectinload(ScenicSpot.spot_images))
        .where(
            ScenicSpot.id == spot_id,
            ScenicSpot.is_active.is_(True),
            ScenicSpot.review_status == "approved",
        )
    )
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")
    pass_settings_by_level = get_active_pass_settings_by_level(db)
    is_unlocked, required_explore_points = get_spot_unlock_state(
        spot_required_explore_points=spot.required_explore_points,
        recommendation_level=spot.recommendation_level,
        user=user,
        fallback_explore_points=user_explore_points,
        settings_by_level=pass_settings_by_level,
    )
    if is_unlocked:
        raise HTTPException(status_code=403, detail="Spot is already unlocked")
    return spot_to_locked_detail_out(
        spot,
        lang=lang,
        user_explore_points=user_explore_points,
        required_explore_points=required_explore_points,
        marker_colors_by_level=get_marker_colors_by_level(db),
        db=db,
    )


@router.get("/{spot_id}", response_model=SpotDetailOut)
def get_spot_detail(
    spot_id: int,
    lang: str = Query(default="zh-CN"),
    user_level: int = Query(default=0, ge=0, le=99),
    is_member: bool = Query(default=False),
    user_id: Optional[int] = Query(default=None),
    explore_points: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SpotDetailOut:
    user, user_explore_points = resolve_user_context(db, user_id, explore_points)
    spot = db.scalar(
        select(ScenicSpot)
        .options(
            selectinload(ScenicSpot.tags),
            selectinload(ScenicSpot.spot_images),
            selectinload(ScenicSpot.wechat_channel_videos),
            selectinload(ScenicSpot.travel_notes).joinedload(TravelNote.user),
            selectinload(ScenicSpot.travel_notes).joinedload(TravelNote.spot),
            selectinload(ScenicSpot.comments).joinedload(UserComment.user),
            selectinload(ScenicSpot.comments).joinedload(UserComment.spot),
            selectinload(ScenicSpot.comments).selectinload(UserComment.likes),
            selectinload(ScenicSpot.lifestyle_recommendations).joinedload(LifestyleRecommendation.spot),
        )
        .where(
            ScenicSpot.id == spot_id,
            ScenicSpot.is_active.is_(True),
            ScenicSpot.review_status == "approved",
        )
    )
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")
    pass_settings_by_level = get_active_pass_settings_by_level(db)
    is_unlocked, required_explore_points = get_spot_unlock_state(
        spot_required_explore_points=spot.required_explore_points,
        recommendation_level=spot.recommendation_level,
        user=user,
        fallback_explore_points=user_explore_points,
        settings_by_level=pass_settings_by_level,
    )
    if not is_unlocked:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Explore points required to unlock this spot",
                "required_explore_points": required_explore_points,
                "user_explore_points": user_explore_points,
            },
        )
    marker_colors_by_level = get_marker_colors_by_level(db)
    my_checkins = []
    if user is not None:
        my_checkins = db.scalars(
            select(CheckinRecord)
            .options(joinedload(CheckinRecord.user), joinedload(CheckinRecord.spot))
            .where(CheckinRecord.spot_id == spot.id, CheckinRecord.user_id == user.id)
            .order_by(CheckinRecord.id.desc())
        ).all()
    return spot_to_detail_out(
        spot,
        lang=lang,
        user_level=user_level,
        is_member=is_member,
        user_explore_points=user_explore_points,
        db=db,
        marker_colors_by_level=marker_colors_by_level,
        pass_settings_by_level=pass_settings_by_level,
        user=user,
        my_checkins=my_checkins,
    )
