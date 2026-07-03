from math import ceil
from typing import TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.schemas.pagination import Page


T = TypeVar("T")


def normalize_page(page: int, page_size: int) -> tuple[int, int]:
    return max(page, 1), min(max(page_size, 1), 100)


def paginated_scalars(
    db: Session,
    statement: Select[tuple[T]],
    page: int,
    page_size: int,
) -> Page[T]:
    page, page_size = normalize_page(page, page_size)
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    items = list(db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all())
    pages = ceil(total / page_size) if total else 0
    return Page(items=items, total=total, page=page, page_size=page_size, pages=pages)


def build_page(items: list[T], total: int, page: int, page_size: int) -> Page[T]:
    page, page_size = normalize_page(page, page_size)
    pages = ceil(total / page_size) if total else 0
    return Page(items=items, total=total, page=page, page_size=page_size, pages=pages)
