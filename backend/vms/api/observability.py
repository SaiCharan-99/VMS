"""Request ids, per-request log lines and latency metrics."""

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from vms.api.views import API_PREFIX
from vms.logging import clear_log_context, new_log_context
from vms.metrics import API_REGISTRY, REQUEST_LATENCY

log = logging.getLogger("vms.request")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _request_id(request: Request) -> str:
    incoming = request.headers.get("x-request-id", "")
    return incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        ctx = new_log_context(request_id=_request_id(request))
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = ctx["request_id"]
            return response
        finally:
            elapsed = time.perf_counter() - start
            route = request.scope.get("route")
            # The route template, not the raw path, keeps label sets small. Included routers
            # report their path without the include prefix, so add it back.
            template = getattr(route, "path", None)
            if template is None:
                template = "unmatched"
            elif request.url.path.startswith(API_PREFIX) and not template.startswith(API_PREFIX):
                template = API_PREFIX + template
            if template != "/metrics":
                REQUEST_LATENCY.labels(request.method, template, str(status)).observe(elapsed)
                log.info(
                    "%s %s %s",
                    request.method,
                    template,
                    status,
                    extra={"duration_ms": round(elapsed * 1000, 1), "status": status},
                )
            clear_log_context()

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        """Prometheus scrape endpoint. Not proxied by the web container: internal only."""
        return Response(generate_latest(API_REGISTRY), media_type=CONTENT_TYPE_LATEST)
