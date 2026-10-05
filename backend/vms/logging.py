"""Logging setup. `VMS_LOG_FORMAT=json` writes one JSON object per line carrying the request,
user and job ids of the current context, so API, worker and proxy logs can be joined."""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# One mutable dict per request or job. Mutating it (rather than setting new ContextVars) lets
# ids bound deep inside an endpoint's thread show up on the middleware's final request line.
_log_context: ContextVar[dict[str, Any] | None] = ContextVar("log_context", default=None)
# Attributes every LogRecord has; anything else came from `extra=` or the context.
_STANDARD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}

_configured = False


def new_log_context(**fields: Any) -> dict[str, Any]:
    ctx = dict(fields)
    _log_context.set(ctx)
    return ctx


def bind_log_context(**fields: Any) -> None:
    ctx = _log_context.get()
    if ctx is None:
        new_log_context(**fields)
    else:
        ctx.update(fields)


def clear_log_context() -> None:
    _log_context.set(None)


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in (_log_context.get() or {}).items():
            if not hasattr(record, key):
                setattr(record, key, value)
        if not hasattr(record, "request_id"):
            record.request_id = None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD and value is not None:
                out[key] = value
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


def configure_logging(level: int = logging.INFO, fmt: str | None = None) -> None:
    """Configure root logging once; safe to call from every entry point."""
    global _configured
    if _configured:
        return
    if fmt is None:
        from vms.config import get_settings

        fmt = get_settings().log_format
    handler = logging.StreamHandler()
    handler.addFilter(_ContextFilter())
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s [req=%(request_id)s] %(message)s")
        )
    logging.basicConfig(level=level, handlers=[handler], force=True)
    if fmt == "json":
        # Route uvicorn's own lines through our handler; its access log duplicates our
        # request line (which carries the ids).
        for name in ("uvicorn", "uvicorn.error"):
            logging.getLogger(name).handlers = []
            logging.getLogger(name).propagate = True
        logging.getLogger("uvicorn.access").disabled = True
    _configured = True
