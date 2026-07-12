from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.content import LifestyleRecommendation, TravelNote, UserComment
from app.models.spot import ScenicSpot, Tag
from app.models.user import MiniProgramUser
from app.schemas.spot import MapSpotOut, SpotDetailOut
from app.services.geo import can_unlock_spot
from app.services.pass_levels import get_marker_colors_by_level
from app.services.spot_mapper import spot_to_detail_out, spot_to_map_out


router = APIRouter()


def resolve_user_explore_points(
    db: Session,
    user_id: Optional[int] = None,
    explore_points: int = 0,
) -> int:
    if user_id is None:
        return explore_points
    user = db.get(MiniProgramUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    return user.explore_points


@router.get("/map", response_model=list[MapSpotOut])
def list_map_spots(
    lang: str = Query(default="zh-CN"),
    tag_ids: list[int] = Query(default=[]),
    user_level: int = Query(default=0, ge=0, le=5),
    is_member: bool = Query(default=False),
    user_id: Optional[int] = Query(default=None),
    explore_points: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[MapSpotOut]:
    user_explore_points = resolve_user_explore_points(db, user_id, explore_points)
    statement = (
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags))
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
    return [
        spot_to_map_out(
            spot,
            lang=lang,
            user_level=user_level,
            is_member=is_member,
            user_explore_points=user_explore_points,
            marker_colors_by_level=marker_colors_by_level,
        )
        for spot in spots
    ]


@router.get("/{spot_id}", response_model=SpotDetailOut)
def get_spot_detail(
    spot_id: int,
    lang: str = Query(default="zh-CN"),
    user_level: int = Query(default=0, ge=0, le=5),
    is_member: bool = Query(default=False),
    user_id: Optional[int] = Query(default=None),
    explore_points: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SpotDetailOut:
    user_explore_points = resolve_user_explore_points(db, user_id, explore_points)
    spot = db.scalar(
        select(ScenicSpot)
        .options(
            selectinload(ScenicSpot.tags),
            selectinload(ScenicSpot.travel_notes).joinedload(TravelNote.user),
            selectinload(ScenicSpot.travel_notes).joinedload(TravelNote.spot),
            selectinload(ScenicSpot.comments).joinedload(UserComment.user),
            selectinload(ScenicSpot.comments).joinedload(UserComment.spot),
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
    if not can_unlock_spot(spot.required_explore_points, user_explore_points):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Explore points required to unlock this spot",
                "required_explore_points": spot.required_explore_points,
                "user_explore_points": user_explore_points,
            },
        )
    marker_colors_by_level = get_marker_colors_by_level(db)
    return spot_to_detail_out(
        spot,
        lang=lang,
        user_level=user_level,
        is_member=is_member,
        user_explore_points=user_explore_points,
        db=db,
        marker_colors_by_level=marker_colors_by_level,
    )
