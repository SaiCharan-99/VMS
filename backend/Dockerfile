# API and worker image. Build from the repo root:
#   docker build -f backend/Dockerfile -t vms-backend --build-arg WITH_ML=1 backend
# WITH_ML=1 adds EasyOCR + YOLO (CPU torch) and bakes their weights in, so the container
# analyses videos offline. WITH_ML=0 gives a small image whose detectors report unavailable.
FROM python:3.12-slim AS base

ARG WITH_ML=1
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    EASYOCR_MODULE_PATH=/opt/models/easyocr \
    YOLO_CONFIG_DIR=/tmp/ultralytics \
    VMS_DATA_DIR=/data \
    VMS_YOLO_WEIGHTS=/opt/models/yolov8n.pt

# libzbar0: barcode decoding. libgl1/libglib2.0-0: the non-headless OpenCV that ultralytics
# pulls in.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libzbar0 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY vms ./vms
COPY alembic ./alembic
COPY alembic.ini ./

# CPU-only torch wheels: the CUDA ones add ~4 GB. For GPU nodes see docs/DEPLOY.md.
RUN if [ "$WITH_ML" = "1" ]; then \
        pip install --extra-index-url https://download.pytorch.org/whl/cpu ".[postgres,ml]"; \
    else \
        pip install ".[postgres]"; \
    fi

RUN mkdir -p /opt/models /data \
    && if [ "$WITH_ML" = "1" ]; then \
        python -c "import easyocr; easyocr.Reader(['en'], gpu=False)" \
        && cd /opt/models && python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"; \
    fi

RUN useradd --system --uid 10001 --home-dir /app vms \
    && chown -R vms:vms /data /opt/models
USER vms

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status != 200)"

# --proxy-headers: client IPs (login rate limit, audit log) come from the web proxy's
# X-Forwarded-For. The API port is only reachable inside the compose network.
CMD ["uvicorn", "vms.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
