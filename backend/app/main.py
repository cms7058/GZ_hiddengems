from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.bootstrap import create_tables, seed_initial_data


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

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    static_dir = Path(__file__).resolve().parent / "static" / "admin"
    media_dir = Path(__file__).resolve().parent / "static" / "uploads"
    app.mount("/admin/static", StaticFiles(directory=static_dir), name="admin-static")
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media_dir), name="media")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/admin")

    @app.get("/admin", include_in_schema=False)
    def admin_page() -> FileResponse:
        return FileResponse(
            static_dir / "index.html",
            media_type="text/html; charset=utf-8",
        )

    @app.on_event("startup")
    def startup() -> None:
        create_tables()
        seed_initial_data()

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
