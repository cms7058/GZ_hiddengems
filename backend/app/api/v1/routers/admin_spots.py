from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.content import LifestyleRecommendation, SpotImage, TravelNote, UserComment
from app.models.spot import ScenicSpot, SpotChildPoint, Tag
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
from app.services.pagination import build_page, paginated_scalars
from app.services.media_storage import MediaStorageError, delete_media
from app.services.spot_mapper import spot_to_admin_out


router = APIRouter()


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


@router.get("", response_model=Page[SpotAdminOut])
def list_admin_spots(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[SpotAdminOut]:
    result = paginated_scalars(
        db,
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags), selectinload(ScenicSpot.child_points))
        .order_by(ScenicSpot.id.desc()),
        page,
        page_size,
    )
    return build_page(
        [spot_to_admin_out(spot) for spot in result.items],
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
    data = payload.model_dump(exclude={"tag_ids"})
    spot = ScenicSpot(**data)
    spot.tags = tags

    db.add(spot)
    db.commit()
    db.refresh(spot)
    db.refresh(spot, attribute_names=["tags"])
    return spot_to_admin_out(spot)


@router.get("/{spot_id}", response_model=SpotAdminOut)
def get_admin_spot(
    spot_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SpotAdminOut:
    spot = db.scalar(
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags), selectinload(ScenicSpot.child_points))
        .where(ScenicSpot.id == spot_id)
    )
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")
    return spot_to_admin_out(spot)


@router.patch("/{spot_id}", response_model=SpotAdminOut)
def update_admin_spot(
    spot_id: int,
    payload: SpotUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SpotAdminOut:
    spot = db.scalar(
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags), selectinload(ScenicSpot.child_points))
        .where(ScenicSpot.id == spot_id)
    )
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")

    update_data = payload.model_dump(exclude_unset=True)
    tag_ids = update_data.pop("tag_ids", None)
    if "recommendation_level" in update_data:
        validate_pass_level(db, update_data["recommendation_level"])
    for field, value in update_data.items():
        setattr(spot, field, value)
    if tag_ids is not None:
        spot.tags = load_tags(db, tag_ids)

    db.add(spot)
    db.commit()
    db.refresh(spot)
    db.refresh(spot, attribute_names=["tags"])
    return spot_to_admin_out(spot)


@router.patch("/{spot_id}/review", response_model=SpotAdminOut)
def review_admin_spot(
    spot_id: int,
    payload: ReviewStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SpotAdminOut:
    spot = db.scalar(
        select(ScenicSpot)
        .options(selectinload(ScenicSpot.tags), selectinload(ScenicSpot.child_points))
        .where(ScenicSpot.id == spot_id)
    )
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")

    spot.review_status = payload.review_status
    db.add(spot)
    db.commit()
    db.refresh(spot)
    db.refresh(spot, attribute_names=["tags"])
    return spot_to_admin_out(spot)


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
    point = SpotChildPoint(spot_id=spot_id, **payload.model_dump())
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
    for field, value in payload.model_dump(exclude_unset=True).items():
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
