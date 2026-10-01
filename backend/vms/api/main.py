"""FastAPI app. Run with `uvicorn vms.api.main:app --reload --port 8000`."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vms import __version__
from vms.api.routers import evidence, health, jobs, legacy, rubrics, videos
from vms.api.views import API_PREFIX
from vms.config import Settings, get_settings
from vms.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()
    app = FastAPI(title="VMS SOP Analyzer API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
    )
    for module in (health, videos, jobs, evidence, rubrics):
        app.include_router(module.router, prefix=API_PREFIX)
    app.include_router(health.router, include_in_schema=False)  # legacy `/health`
    app.include_router(legacy.router)
    return app


app = create_app()
