from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.spot import ScenicSpot, Tag
from app.schemas.spot import MapSpotOut, SpotDetailOut
from app.services.spot_mapper import spot_to_detail_out, spot_to_map_out


router = APIRouter()


@router.get("/map", response_model=list[MapSpotOut])
def list_map_spots(
    lang: str = Query(default="zh-CN"),
    tag_ids: list[int] = Query(default=[]),
    user_level: int = Query(default=0, ge=0, le=5),
    is_member: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[MapSpotOut]:
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
    return [
        spot_to_map_out(
            spot,
            lang=lang,
            user_level=user_level,
            is_member=is_member,
        )
        for spot in spots
    ]


@router.get("/{spot_id}", response_model=SpotDetailOut)
def get_spot_detail(
    spot_id: int,
    lang: str = Query(default="zh-CN"),
    user_level: int = Query(default=0, ge=0, le=5),
    is_member: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> SpotDetailOut:
    spot = db.scalar(
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags))
        .where(
            ScenicSpot.id == spot_id,
            ScenicSpot.is_active.is_(True),
            ScenicSpot.review_status == "approved",
        )
    )
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")
    return spot_to_detail_out(spot, lang=lang, user_level=user_level, is_member=is_member)
