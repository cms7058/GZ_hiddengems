from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.spot import Tag
from app.schemas.spot import LocalizedTag
from app.services.localization import normalize_language
from app.services.spot_mapper import tag_to_localized


router = APIRouter()


@router.get("", response_model=list[LocalizedTag])
def list_tags(
    lang: str = Query(default="zh-CN"),
    db: Session = Depends(get_db),
) -> list[LocalizedTag]:
    normalized_lang = normalize_language(lang)
    tags = db.scalars(
        select(Tag)
        .where(Tag.is_active.is_(True))
        .order_by(Tag.sort_order.asc(), Tag.id.asc())
    ).all()
    return [tag_to_localized(tag, normalized_lang) for tag in tags]
