from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.schemas.auth import AdminLoginIn, AdminProfileUpdate, AdminUserOut, TokenOut
from app.services.security import create_access_token, hash_password, verify_password


router = APIRouter()


def admin_to_out(admin: AdminUser) -> AdminUserOut:
    return AdminUserOut(id=admin.id, username=admin.username, role=admin.role)


@router.post("/admin/login", response_model=TokenOut)
def admin_login(payload: AdminLoginIn, db: Session = Depends(get_db)) -> TokenOut:
    admin = db.scalar(
        select(AdminUser).where(
            AdminUser.username == payload.username,
            AdminUser.is_active.is_(True),
        )
    )
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return TokenOut(
        access_token=create_access_token(str(admin.id)),
        admin=admin_to_out(admin),
    )


@router.get("/admin/me", response_model=AdminUserOut)
def get_admin_me(current_admin: AdminUser = Depends(get_current_admin)) -> AdminUserOut:
    return admin_to_out(current_admin)


@router.patch("/admin/me", response_model=AdminUserOut)
def update_admin_me(
    payload: AdminProfileUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminUserOut:
    username = payload.username.strip() if payload.username else None
    if username and username != current_admin.username:
        existing = db.scalar(
            select(AdminUser).where(
                AdminUser.username == username,
                AdminUser.id != current_admin.id,
            )
        )
        if existing is not None:
            raise HTTPException(status_code=400, detail="Username already exists")
        current_admin.username = username

    if payload.new_password:
        if not payload.current_password or not verify_password(payload.current_password, current_admin.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        current_admin.password_hash = hash_password(payload.new_password)

    db.add(current_admin)
    db.commit()
    db.refresh(current_admin)
    return admin_to_out(current_admin)
