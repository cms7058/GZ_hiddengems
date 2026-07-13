from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.spot import Tag
from app.schemas.spot import TagAdminOut, TagCreate, TagUpdate
from app.schemas.pagination import Page
from app.services.pagination import build_page, paginated_scalars
from app.services.spot_mapper import tag_to_admin_out


router = APIRouter()


@router.get("", response_model=Page[TagAdminOut])
def list_admin_tags(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[TagAdminOut]:
    result = paginated_scalars(db, select(Tag).order_by(Tag.sort_order.asc(), Tag.id.asc()), page, page_size)
    return build_page(
        [tag_to_admin_out(tag) for tag in result.items],
        result.total,
        result.page,
        result.page_size,
    )


def validate_sort_order(db: Session, sort_order: int, exclude_tag_id: Optional[int] = None) -> None:
    statement = select(Tag).where(Tag.sort_order == sort_order)
    if exclude_tag_id is not None:
        statement = statement.where(Tag.id != exclude_tag_id)
    if db.scalar(statement.limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Tag sort order already exists")


@router.post("", response_model=TagAdminOut, status_code=201)
def create_admin_tag(
    payload: TagCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> TagAdminOut:
    exists = db.scalar(select(Tag).where(Tag.name_zh == payload.name_zh))
    if exists:
        raise HTTPException(status_code=409, detail="Tag already exists")
    validate_sort_order(db, payload.sort_order)

    tag = Tag(**payload.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag_to_admin_out(tag)


@router.patch("/{tag_id}", response_model=TagAdminOut)
def update_admin_tag(
    tag_id: int,
    payload: TagUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> TagAdminOut:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "sort_order" in update_data:
        validate_sort_order(db, update_data["sort_order"], tag.id)
    for field, value in update_data.items():
        setattr(tag, field, value)

    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag_to_admin_out(tag)


@router.delete("/{tag_id}", status_code=204)
def delete_admin_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    tag = db.scalar(select(Tag).options(selectinload(Tag.spots)).where(Tag.id == tag_id))
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")

    tag.spots.clear()
    db.delete(tag)
    db.commit()
