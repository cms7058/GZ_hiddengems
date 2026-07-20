from fastapi import APIRouter

from app.api.v1.routers import (
    admin_checkins,
    admin_assistant,
    admin_archive,
    admin_content,
    admin_integrations,
    admin_growth,
    admin_memberships,
    admin_pass_settings,
    admin_roles,
    admin_spots,
    admin_tags,
    admin_users,
    auth,
    mini,
    mini_archive,
    safety,
    spots,
    tags,
)


api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(spots.router, prefix="/spots", tags=["spots"])
api_router.include_router(mini.router, prefix="/mini", tags=["mini-program"])
api_router.include_router(mini_archive.router, prefix="/mini/archive", tags=["mini-archive"])
api_router.include_router(safety.router, tags=["safety"])
api_router.include_router(admin_tags.router, prefix="/admin/tags", tags=["admin-tags"])
api_router.include_router(admin_spots.router, prefix="/admin/spots", tags=["admin-spots"])
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin-users"])
api_router.include_router(admin_roles.router, prefix="/admin/roles", tags=["admin-roles"])
api_router.include_router(
    admin_pass_settings.router,
    prefix="/admin/pass-settings",
    tags=["admin-pass-settings"],
)
api_router.include_router(
    admin_memberships.router,
    prefix="/admin/memberships",
    tags=["admin-memberships"],
)
api_router.include_router(admin_checkins.router, prefix="/admin/checkins", tags=["admin-checkins"])
api_router.include_router(admin_growth.router, prefix="/admin/growth", tags=["admin-growth"])
api_router.include_router(admin_assistant.router, prefix="/admin/assistant", tags=["admin-assistant"])
api_router.include_router(admin_archive.router, prefix="/admin/archive", tags=["admin-archive"])
api_router.include_router(admin_content.router, prefix="/admin/content", tags=["admin-content"])
api_router.include_router(
    admin_integrations.router,
    prefix="/admin/integrations",
    tags=["admin-integrations"],
)
