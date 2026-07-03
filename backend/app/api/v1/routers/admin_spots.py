from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.spot import ScenicSpot, Tag
from app.schemas.spot import ReviewStatusUpdate, SpotAdminOut, SpotCreate, SpotUpdate
from app.schemas.pagination import Page
from app.services.pagination import build_page, paginated_scalars
from app.services.spot_mapper import spot_to_admin_out


router = APIRouter()


def load_tags(db: Session, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    tags = db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all()
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=400, detail="One or more tags do not exist")
    return tags


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
        .options(selectinload(ScenicSpot.tags))
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
        .options(selectinload(ScenicSpot.tags))
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
        .options(selectinload(ScenicSpot.tags))
        .where(ScenicSpot.id == spot_id)
    )
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")

    update_data = payload.model_dump(exclude_unset=True)
    tag_ids = update_data.pop("tag_ids", None)
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
        .options(selectinload(ScenicSpot.tags))
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


@router.delete("/{spot_id}", status_code=204)
def delete_admin_spot(
    spot_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    spot = db.get(ScenicSpot, spot_id)
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")

    spot.is_active = False
    db.add(spot)
    db.commit()
