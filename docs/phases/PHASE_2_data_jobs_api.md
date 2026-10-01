# Phase 2 — Data Layer, Job Worker & API v1

**Goal:** Persist videos, jobs, analyses, and evidence. Run analysis asynchronously in a worker process. Expose the `/api/v1` video and job endpoints. Keep the legacy endpoints working.

**Read:** IMPLEMENTATION.md §3, §7 (data model), §8 (API), §10.
**Branch:** `phase-2-data-jobs-api`

## Tasks

- [ ] Deps: sqlalchemy>=2, alembic, (psycopg[binary] as an optional `[postgres]` extra).
- [ ] `vms/db/`: engine and session factory from `settings.db_url` (default `sqlite:///data/vms.db`; SQLite needs `check_same_thread=False` and WAL mode). Add declarative models for **all** §7 tables, including users and warehouses, so Phase 3 needs no schema churn. Users get a seeded `system` admin.
- [ ] Alembic: `backend/alembic.ini` + env reading settings. Initial migration. Tests use `Base.metadata.create_all` on a temp SQLite DB, plus one test that runs `alembic upgrade head` on an empty DB.
- [ ] `vms/storage.py`: `Storage` protocol (`save_stream(key, fileobj) -> size, sha256`, `open(key)`, `path(key)`, `delete(key)`, `exists`) and `LocalStorage(root=settings.data_dir)`. Keys: `videos/YYYY/MM/<uuid><ext>` and `evidence/<analysis_uuid>/<step>_<n>.jpg`.
- [ ] Services (`vms/services/`): `videos.create_from_upload` (stream to storage, hash, dedupe, enqueue), `jobs.claim_next` (atomic, §7), `jobs.heartbeat`, `jobs.complete`/`fail`, `jobs.requeue_stale`, `analyses.save_result` (write analysis + evidence rows, update `videos.final_status`), `audit.log`.
- [ ] `vms/worker.py`: `python -m vms.worker [--once] [--poll 1.5]`. Loop: requeue stale, claim, run `analyze_video` with `progress_cb` → job.progress (throttled writes), save, and handle exceptions (job failed, with the error message). Handle SIGINT/SIGTERM gracefully. Several worker processes must be safe to run at once.
- [ ] API (`vms/api/`): app factory `create_app(settings)`, routers `health`, `videos`, `jobs`, `evidence`, `rubrics`, and `legacy` (`POST /analyze` sync + `GET /results` reading the new tables). `deps.get_current_user` returns the system admin (Phase 3 replaces it). Uploads are streamed with size-limit enforcement, extension and content checks (try `cv2.VideoCapture` on the saved file, and reject with 400 + delete if it won't open). `/videos/{id}/stream` supports Range. CORS from `settings.cors_origins`.
- [ ] Pagination helper and filter parsing for `GET /videos` (status, process_type, awb, q matches filename/awb/barcode, dates).
- [ ] When an analysis detects a barcode and the video has no `awb`, set `awb` to the first barcode value.
- [ ] `vms/cli.py import-legacy --db audit_results.db`: import old `results` rows as videos (`source=legacy`, no file) plus analyses (`schema_version 1.0`). Idempotent.
- [ ] Remove `vms/legacy_store.py` once nothing uses it.
- [ ] Tests:
  - Storage round-trip.
  - Upload → job queued → `worker --once` → analysis saved → `GET /videos/{id}` returns the result plus evidence URLs. Use the synthetic QR video with models off.
  - Duplicate upload is deduped. Oversize upload gets 413. A non-video gets 400.
  - Two threads calling `claim_next` never get the same job.
  - Stale job requeue and max_attempts → failed.
  - A corrupt video leads to a failed job with an error message.
  - Filters and pagination. Range request returns 206.
  - Legacy `/analyze` returns the v1 shape.

## Acceptance criteria

1. With API and worker running, `curl -F file=@x.mp4 -F process_type=Return localhost:8000/api/v1/videos` returns 201 immediately. Polling `/api/v1/jobs/{id}` reaches `done`, and `/api/v1/videos/{id}` shows the result.
2. Killing the worker mid-job and restarting it eventually completes the job.
3. Swagger at `/docs` lists all Phase 2 endpoints with typed schemas.
4. All tests are green, and ruff is clean.

## Out of scope

Real auth (stubbed), the UI, reviews, and reports.

## Handoff notes

How to run API + worker locally (exact commands), env vars added (also add them to `.env.example`), and any deviations from §7/§8.
