import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminRole, AdminUser
from app.schemas.admin_roles import (
    AdminAccountIn,
    AdminAccountOut,
    AdminAccountUpdate,
    AdminRoleIn,
    AdminRoleOut,
    AdminRoleUpdate,
)
from app.services.permissions import normalize_permissions, role_permissions
from app.services.security import hash_password


router = APIRouter()


def require_super_admin(admin: AdminUser) -> None:
    if admin.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin permission required")


def role_to_out(role: AdminRole) -> AdminRoleOut:
    return AdminRoleOut(
        id=role.id,
        code=role.code,
        name=role.name,
        permissions=role_permissions(role, AdminUser(role="role", id=0)),
        is_active=role.is_active,
    )


@router.get("", response_model=list[AdminRoleOut])
def list_roles(db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> list[AdminRoleOut]:
    require_super_admin(current_admin)
    return [role_to_out(role) for role in db.scalars(select(AdminRole).order_by(AdminRole.id)).all()]


@router.post("", response_model=AdminRoleOut, status_code=201)
def create_role(payload: AdminRoleIn, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> AdminRoleOut:
    require_super_admin(current_admin)
    if payload.code == "super_admin" or db.scalar(select(AdminRole).where(AdminRole.code == payload.code)) is not None:
        raise HTTPException(status_code=409, detail="Role code already exists or is reserved")
    role = AdminRole(code=payload.code, name=payload.name, permissions_json=json.dumps(normalize_permissions(payload.permissions)), is_active=payload.is_active)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role_to_out(role)


@router.patch("/{role_id:int}", response_model=AdminRoleOut)
def update_role(role_id: int, payload: AdminRoleUpdate, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> AdminRoleOut:
    require_super_admin(current_admin)
    role = db.get(AdminRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    if payload.name is not None:
        role.name = payload.name
    if payload.permissions is not None:
        role.permissions_json = json.dumps(normalize_permissions(payload.permissions))
    if payload.is_active is not None:
        role.is_active = payload.is_active
    db.add(role)
    db.commit()
    db.refresh(role)
    return role_to_out(role)


@router.delete("/{role_id:int}", status_code=204)
def delete_role(role_id: int, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> None:
    require_super_admin(current_admin)
    role = db.get(AdminRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    if db.scalar(select(AdminUser).where(AdminUser.role == role.code)) is not None:
        raise HTTPException(status_code=409, detail="Reassign administrators before deleting this role")
    db.delete(role)
    db.commit()


@router.get("/admins", response_model=list[AdminAccountOut])
def list_admins(db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> list[AdminAccountOut]:
    require_super_admin(current_admin)
    return [AdminAccountOut(id=item.id, username=item.username, role=item.role, is_active=item.is_active) for item in db.scalars(select(AdminUser).order_by(AdminUser.id)).all()]


@router.post("/admins", response_model=AdminAccountOut, status_code=201)
def create_admin(payload: AdminAccountIn, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> AdminAccountOut:
    require_super_admin(current_admin)
    if db.scalar(select(AdminUser).where(AdminUser.username == payload.username)) is not None:
        raise HTTPException(status_code=409, detail="Username already exists")
    if payload.role != "super_admin" and db.scalar(select(AdminRole).where(AdminRole.code == payload.role, AdminRole.is_active.is_(True))) is None:
        raise HTTPException(status_code=400, detail="Role does not exist or is inactive")
    admin = AdminUser(username=payload.username, password_hash=hash_password(payload.password), role=payload.role)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return AdminAccountOut(id=admin.id, username=admin.username, role=admin.role, is_active=admin.is_active)


@router.patch("/admins/{admin_id}", response_model=AdminAccountOut)
def update_admin(admin_id: int, payload: AdminAccountUpdate, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> AdminAccountOut:
    require_super_admin(current_admin)
    admin = db.get(AdminUser, admin_id)
    if admin is None:
        raise HTTPException(status_code=404, detail="Admin user not found")
    if payload.username is not None:
        username = payload.username.strip()
        if not username:
            raise HTTPException(status_code=400, detail="Username cannot be empty")
        if db.scalar(select(AdminUser).where(AdminUser.username == username, AdminUser.id != admin.id)) is not None:
            raise HTTPException(status_code=409, detail="Username already exists")
        admin.username = username
    if payload.password is not None:
        admin.password_hash = hash_password(payload.password)
    if payload.role is not None:
        if payload.role != "super_admin" and db.scalar(select(AdminRole).where(AdminRole.code == payload.role, AdminRole.is_active.is_(True))) is None:
            raise HTTPException(status_code=400, detail="Role does not exist or is inactive")
        admin.role = payload.role
    if payload.is_active is not None:
        if admin.id == current_admin.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="Cannot disable your own account")
        admin.is_active = payload.is_active
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return AdminAccountOut(id=admin.id, username=admin.username, role=admin.role, is_active=admin.is_active)
