from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.schemas.auth import AdminLoginIn, AdminUserOut, TokenOut
from app.services.security import create_access_token, verify_password


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
