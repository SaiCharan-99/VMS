import logging

_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging once; safe to call from every entry point."""
    global _configured
    if _configured:
        return
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    _configured = True
