"""FastAPI app. Run with `uvicorn vms.api.main:app --reload --port 8000`."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vms import __version__
from vms.api import observability
from vms.api.ratelimit import LoginLimiter
from vms.api.routers import (
    admin,
    auth,
    evidence,
    health,
    jobs,
    reports,
    review_queue,
    rubrics,
    stations,
    videos,
)
from vms.api.views import API_PREFIX
from vms.config import Settings, get_settings
from vms.logging import configure_logging
from vms.security import InsecureConfigError, jwt_secret


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()
    jwt_secret()  # fail fast outside dev when VMS_JWT_SECRET is missing or weak
    if settings.env != "dev" and "*" in settings.cors_origins:
        raise InsecureConfigError("VMS_CORS_ORIGINS may not contain '*' outside dev.")
    app = FastAPI(title="VMS SOP Analyzer API", version=__version__)
    app.state.login_limiter = LoginLimiter(settings.login_max_failures, settings.login_window_s)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID", "Range"],
        expose_headers=["Content-Range", "Accept-Ranges", "Content-Length", "X-Request-ID"],
    )
    observability.install(app)
    for module in (
        health,
        auth,
        videos,
        review_queue,
        reports,
        jobs,
        evidence,
        rubrics,
        stations,
        admin,
    ):
        app.include_router(module.router, prefix=API_PREFIX)
    return app


app = create_app()
