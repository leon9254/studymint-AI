from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.BACKEND_CORS_ORIGIN_REGEX or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    settings.export_dir_path.mkdir(parents=True, exist_ok=True)
    app.mount(settings.PDF_EXPORT_BASE_URL, StaticFiles(directory=str(settings.export_dir_path)), name="exports")

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok", "service": settings.APP_NAME}

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
