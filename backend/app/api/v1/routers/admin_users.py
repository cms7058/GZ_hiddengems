from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.user import MiniProgramUser
from app.schemas.pagination import Page
from app.schemas.user import MiniProgramUserCreate, MiniProgramUserOut, MiniProgramUserUpdate
from app.services.media_storage import get_media_display_url
from app.services.pagination import paginated_scalars
from app.services.memberships import sync_user_membership_by_points
from app.services.safety_levels import apply_safety_level_policy


router = APIRouter()


def user_to_out(db: Session, user: MiniProgramUser) -> MiniProgramUserOut:
    result = MiniProgramUserOut.model_validate(user)
    return result.model_copy(update={"avatar_url": get_media_display_url(db, user.avatar_url)})


@router.get("", response_model=Page[MiniProgramUserOut])
def list_admin_users(
    keyword: str = Query(default=""),
    include_inactive: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[MiniProgramUserOut]:
    statement = select(MiniProgramUser).order_by(MiniProgramUser.id.desc())
    if not include_inactive:
        statement = statement.where(MiniProgramUser.is_active.is_(True))
    if keyword:
        like_keyword = f"%{keyword}%"
        statement = statement.where(
            or_(
                MiniProgramUser.nickname.like(like_keyword),
                MiniProgramUser.openid.like(like_keyword),
                MiniProgramUser.phone.like(like_keyword),
            )
        )
    result = paginated_scalars(db, statement, page, page_size)
    return Page(
        items=[user_to_out(db, user) for user in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        pages=result.pages,
    )


@router.get("/{user_id}", response_model=MiniProgramUserOut)
def get_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> MiniProgramUserOut:
    user = db.get(MiniProgramUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_out(db, user)


@router.post("", response_model=MiniProgramUserOut, status_code=201)
def create_admin_user(
    payload: MiniProgramUserCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> MiniProgramUserOut:
    exists = db.scalar(select(MiniProgramUser).where(MiniProgramUser.openid == payload.openid))
    if exists is not None and exists.is_active:
        raise HTTPException(status_code=409, detail="OpenID already exists")
    if exists is not None:
        for field, value in payload.model_dump().items():
            setattr(exists, field, value)
        exists.is_active = True
        db.add(exists)
        db.flush()
        apply_safety_level_policy(db, exists)
        sync_user_membership_by_points(db, exists)
        db.commit()
        db.refresh(exists)
        return user_to_out(db, exists)

    user = MiniProgramUser(**payload.model_dump())
    db.add(user)
    db.flush()
    apply_safety_level_policy(db, user)
    sync_user_membership_by_points(db, user)
    db.commit()
    db.refresh(user)
    return user_to_out(db, user)


@router.patch("/{user_id}", response_model=MiniProgramUserOut)
def update_admin_user(
    user_id: int,
    payload: MiniProgramUserUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> MiniProgramUserOut:
    user = db.get(MiniProgramUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    if "explore_points" in payload.model_dump(exclude_unset=True):
        sync_user_membership_by_points(db, user)
    if "safety_level" in payload.model_dump(exclude_unset=True):
        apply_safety_level_policy(db, user)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_out(db, user)


@router.delete("/{user_id}", status_code=204)
def delete_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    user = db.get(MiniProgramUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.add(user)
    db.commit()
