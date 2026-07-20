from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.bootstrap import create_tables, seed_initial_data
from app.services.integrations import get_mini_program_service_hours


BEIJING_TIMEZONE = timezone(timedelta(hours=8))


def public_api_is_open(open_hour: int, close_hour: int, now: Optional[datetime] = None) -> bool:
    current_hour = (now or datetime.now(BEIJING_TIMEZONE)).astimezone(BEIJING_TIMEZONE).hour
    return open_hour <= current_hour < close_hour


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def enforce_public_api_service_hours(request: Request, call_next):
        path = request.url.path
        api_prefix = settings.api_v1_prefix.rstrip("/")
        admin_prefix = f"{api_prefix}/admin"
        service_hours_path = f"{api_prefix}/mini/service-hours"
        media_prefix = f"{api_prefix}/media/"
        is_public_api = path.startswith(f"{api_prefix}/") and not (
            path == admin_prefix or path.startswith(f"{admin_prefix}/")
        )
        if is_public_api and path != service_hours_path and not path.startswith(media_prefix):
            with SessionLocal() as db:
                service_hours = get_mini_program_service_hours(db)
            if service_hours["enabled"] and not public_api_is_open(
                service_hours["open_hour"], service_hours["close_hour"]
            ):
                return JSONResponse(
                    status_code=403,
                    content={
                        "code": "SERVICE_CLOSED",
                        "detail": "Public data service is outside the configured Beijing-time window",
                        "open_hour": service_hours["open_hour"],
                        "close_hour": service_hours["close_hour"],
                    },
                )
        return await call_next(request)

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    static_dir = Path(__file__).resolve().parent / "static" / "admin"
    media_dir = Path(__file__).resolve().parent / "static" / "uploads"
    app.mount("/admin/static", StaticFiles(directory=static_dir), name="admin-static")
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media_dir), name="media")

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return FileResponse(
            static_dir / "index.html",
            media_type="text/html; charset=utf-8",
        )

    @app.get("/admin", include_in_schema=False)
    def admin_page() -> FileResponse:
        return FileResponse(
            static_dir / "index.html",
            media_type="text/html; charset=utf-8",
        )

    @app.get("/admin/archive", include_in_schema=False)
    def archive_page() -> FileResponse:
        return FileResponse(
            static_dir / "requirements-prototype.html",
            media_type="text/html; charset=utf-8",
        )

    @app.on_event("startup")
    def startup() -> None:
        create_tables()
        seed_initial_data()

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
