from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.spot import Tag
from app.schemas.spot import TagAdminOut, TagCreate, TagUpdate
from app.services.spot_mapper import tag_to_admin_out


router = APIRouter()


@router.get("", response_model=list[TagAdminOut])
def list_admin_tags(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[TagAdminOut]:
    tags = db.scalars(select(Tag).order_by(Tag.sort_order.asc(), Tag.id.asc())).all()
    return [tag_to_admin_out(tag) for tag in tags]


@router.post("", response_model=TagAdminOut, status_code=201)
def create_admin_tag(
    payload: TagCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> TagAdminOut:
    exists = db.scalar(select(Tag).where(Tag.name_zh == payload.name_zh))
    if exists:
        raise HTTPException(status_code=409, detail="Tag already exists")

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
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")

    tag.is_active = False
    db.add(tag)
    db.commit()
