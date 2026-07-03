from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.user import MiniProgramUser
from app.schemas.user import MiniProgramUserOut, MiniProgramUserUpdate


router = APIRouter()


@router.get("", response_model=list[MiniProgramUserOut])
def list_admin_users(
    keyword: str = Query(default=""),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[MiniProgramUserOut]:
    statement = select(MiniProgramUser).order_by(MiniProgramUser.id.desc())
    if keyword:
        like_keyword = f"%{keyword}%"
        statement = statement.where(
            or_(
                MiniProgramUser.nickname.like(like_keyword),
                MiniProgramUser.openid.like(like_keyword),
                MiniProgramUser.phone.like(like_keyword),
            )
        )
    return list(db.scalars(statement).all())


@router.get("/{user_id}", response_model=MiniProgramUserOut)
def get_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> MiniProgramUserOut:
    user = db.get(MiniProgramUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


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

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
