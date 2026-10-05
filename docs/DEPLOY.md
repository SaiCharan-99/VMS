# Deploying VMS SOP Analyzer

The production stack is `docker-compose.yml` on one Docker host: `postgres`, a one-shot
`migrate`, `api` (FastAPI), `worker` (scalable), and `web` (nginx serving the UI and proxying
`/api`). Only `web` publishes a port.

> `docker compose up` also loads `docker-compose.override.yml`, which switches to dev mode
> (demo logins allowed, text logs, API and Postgres ports published). **In production always pass
> `-f docker-compose.yml`.**

## 1. Install

```bash
git clone https://github.com/SaiCharan-99/VMS.git && cd VMS
cp .env.example .env
```

Edit `.env`:

| Setting | Value |
|---|---|
| `VMS_ENV` | `prod` (anything except `dev`) |
| `VMS_JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"`; the API refuses to start if it is missing, shorter than 32 chars, or a placeholder |
| `POSTGRES_PASSWORD` | a strong random password |
| `VMS_HTTP_PORT` | host port for the web UI (80) |
| `VMS_RETENTION_DAYS` | days to keep settled video files (unset = forever) |
| `WITH_ML` | `1` (default) bakes EasyOCR + YOLO weights into the image |

Start and create the first admin:

```bash
docker compose -f docker-compose.yml up -d --build --wait
docker compose -f docker-compose.yml exec api python -m vms.cli create-admin --email admin@company.com --name "Admin"
```

Open `http://<host>/`. Put a TLS-terminating proxy or load balancer in front for HTTPS. The
`web` container listens on plain HTTP; the CSP and other security headers are already set.

## 2. Scaling analysis

Each worker handles one video at a time (about 30–60 s of CPU per minute of video at 3 fps).
Job claims use `SELECT … FOR UPDATE SKIP LOCKED`, so any number of workers can run:

```bash
docker compose -f docker-compose.yml up -d --scale worker=4
```

Each worker needs ~1.5 GB RAM with the ML models loaded. On `docker compose stop`, a worker
puts its current job back in the queue. A worker that dies is detected by heartbeat after
`VMS_JOB_STALE_S` (300 s) and its job is retried (up to `VMS_JOB_MAX_ATTEMPTS`).

## 3. Backup and restore

Two things hold state: the Postgres volume (`pg-data`) and the data volume (`vms-data`: videos,
evidence frames). Back up both, and do it at the same time.

```bash
# Postgres
docker compose -f docker-compose.yml exec -T postgres pg_dump -U vms -Fc vms > vms-$(date +%F).dump
# Data volume
docker run --rm -v vms_vms-data:/data -v "$PWD":/backup alpine tar czf /backup/vms-data-$(date +%F).tgz -C /data .
```

(The volume name is `<project>_vms-data`; check with `docker volume ls`.)

Restore into a fresh stack:

```bash
docker compose -f docker-compose.yml up -d postgres
docker compose -f docker-compose.yml exec -T postgres pg_restore -U vms -d vms --clean --if-exists < vms-2026-10-05.dump
docker run --rm -v vms_vms-data:/data -v "$PWD":/backup alpine tar xzf /backup/vms-data-2026-10-05.tgz -C /data
docker compose -f docker-compose.yml up -d --wait
```

## 4. Upgrade

```bash
git pull
docker compose -f docker-compose.yml up -d --build --wait
```

The `migrate` service runs `alembic upgrade head` before `api` and `worker` start. Take a backup
first. Roll back with the previous image tag plus `alembic downgrade <revision>` only if the
release notes say the migration is reversible.

## 5. Retention

Run daily from cron on the host (or any scheduler):

```bash
docker compose -f docker-compose.yml exec -T api python -m vms.cli purge
```

This uses `VMS_RETENTION_DAYS` (or `--older-than-days N`). It deletes **only the video file**;
the database rows, analysis, human reviews and evidence frames stay. A file is never deleted
while the video is pending, awaiting review, has a queued or running job, or is **disputed**.
Each deletion is written to the audit log (`video.file_purged`). Add `--dry-run` to preview.

## 6. Monitoring

- `GET /api/v1/health` checks the DB, that the data volume is writable, and detector status. It
  returns 503 when degraded and is used by the container healthchecks.
- Prometheus metrics are internal only (nginx does not proxy them):
  - `api:8000/metrics`: request latency per route (`vms_http_request_duration_seconds`) and
    jobs by status (`vms_jobs{status=…}`).
  - `worker:9100/metrics` (each worker): `vms_analysis_duration_seconds`.
- Logs are JSON lines (`VMS_LOG_FORMAT=json`) with `request_id` (also the `X-Request-ID`
  response header, set by nginx), `user_id`, `api_key_id`, and `job_id`/`video_id` in the worker.

## 7. GPU

The image installs CPU-only PyTorch. For an NVIDIA GPU node, build with the CUDA wheels (edit the
`pip install` line in `backend/Dockerfile` to drop the CPU index), add
`deploy.resources.reservations.devices` for the `worker` service, and change `gpu=False` in
`vms/analysis/detectors/ocr.py`. YOLO picks the GPU automatically. Workers are the only
GPU-bound part; the API never loads models.

## 8. Custom detector

Copy trained weights and their model card into the data volume, e.g.
`/data/models/vms-det-2026-10-01.pt` and `vms-det-2026-10-01.model_card.json`, then set
`VMS_YOLO_WEIGHTS=/data/models/vms-det-2026-10-01.pt` in `.env` and restart the workers. Switch
to the `-v2` rubrics (`VMS_RUBRIC_FORWARD`, `VMS_RUBRIC_RETURN`) only with such a model: see
PROGRESS.md.

## Security notes

- Login attempts are limited per process by the API and across replicas by nginx (`limit_req`,
  10/min per IP on `/api/v1/auth/login`).
- `<video>` and `<img>` media use short-lived HMAC-signed URLs (`VMS_MEDIA_URL_TTL_S`), so JWTs
  never appear in query strings.
- Uploads are capped by nginx (`client_max_body_size` = `VMS_MAX_UPLOAD_MB`) and again by the API.
  Only video extensions are accepted, and every file is probed with OpenCV before it is queued.
- The API trusts `X-Forwarded-For` from any peer (`--forwarded-allow-ips "*"`). That is safe
  because the API port is reachable only inside the compose network. Don't publish it in
  production.
