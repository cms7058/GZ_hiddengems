import json
from typing import Iterable, Optional

from app.models.admin import AdminRole, AdminUser


RESOURCES = (
    "users",
    "tags",
    "pass_settings",
    "memberships",
    "checkins",
    "recommendations",
    "integrations",
    "growth",
)
ACTIONS = ("read", "create", "update", "delete")
ALL_PERMISSIONS = tuple(f"{resource}:{action}" for resource in RESOURCES for action in ACTIONS)


def normalize_permissions(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value in ALL_PERMISSIONS})


def role_permissions(role: Optional[AdminRole], admin: AdminUser) -> list[str]:
    if admin.role == "super_admin":
        return list(ALL_PERMISSIONS)
    if role is None or not role.is_active:
        return []
    try:
        values = json.loads(role.permissions_json or "[]")
    except json.JSONDecodeError:
        values = []
    return normalize_permissions(values if isinstance(values, list) else [])


def permission_for_request(path: str, method: str) -> Optional[str]:
    resource = None
    if "/admin/users" in path:
        resource = "users"
    elif "/admin/tags" in path:
        resource = "tags"
    elif "/admin/pass-settings" in path:
        resource = "pass_settings"
    elif "/admin/memberships" in path:
        resource = "memberships"
    elif "/admin/checkins" in path or "/admin/content" in path:
        resource = "recommendations" if "/recommendations" in path else "checkins"
    elif "/admin/integrations" in path:
        resource = "integrations"
    elif "/admin/growth" in path:
        resource = "growth"
    if resource is None:
        return None
    action = {"GET": "read", "POST": "create", "PATCH": "update", "PUT": "update", "DELETE": "delete"}.get(method)
    return f"{resource}:{action}" if action else None
