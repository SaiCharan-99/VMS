# Phase 7 — Production Hardening & Deployment

**Goal:** Make the app deployable, observable, and maintainable. That means Docker Compose, Postgres, CI, retention, security review, docs, and removing the legacy code.

**Read:** IMPLEMENTATION.md §3, §10, §11 (deployment answers recorded in PROGRESS.md → Decisions).
**Branch:** `phase-7-production`

## Tasks

- [ ] **Docker:** `backend/Dockerfile` (python-slim + libzbar0 + libgl; a build arg `WITH_ML=1`; non-root user; pre-download EasyOCR weights at build time so the container works offline). `frontend/Dockerfile` (build → nginx serving `dist/` and proxying `/api`). `docker-compose.yml`: `postgres`, `api`, `worker` (scalable `--scale worker=N`), `web`, with volumes for `data/` and the Postgres data. Add a `docker-compose.override.yml` for dev.
- [ ] **Postgres:** verify all migrations and the report queries on Postgres (CI job against a postgres service). Use `SELECT … FOR UPDATE SKIP LOCKED` for job claiming on Postgres and keep the SQLite path.
- [ ] **Config & secrets:** a complete `.env.example`. App startup fails fast on a missing or weak `JWT_SECRET` in prod. Lock CORS to the configured origins.
- [ ] **Observability:** structured JSON logs (request id, user id, job id). `/api/v1/health` with DB, storage-writable, and detector status. `/metrics` (prometheus-client): request latency, jobs queued/running/failed, analysis duration histogram.
- [ ] **Retention:** `python -m vms.cli purge --older-than-days N` deletes video files (keeping DB rows, the analysis, and evidence), honouring `VMS_RETENTION_DAYS`. Videos with an open review or a dispute flag are never purged. Write to the audit log.
- [ ] **Webhooks (if confirmed in Open Questions):** `webhooks` table + admin UI, and a POST on `analysis.completed` / `review.completed` with an HMAC signature and retries.
- [ ] **Security pass:** run the `security-review` skill. Check upload content validation, path traversal in storage keys, the auth on `/stream` and `/evidence` (signed short-lived URLs or cookie auth so `<video>` tags work without exposing the JWT in query strings), rate limits, and dependency audit (`pip-audit`, `npm audit`).
- [ ] **Type sync:** generate frontend API types from OpenAPI (`openapi-typescript`) and add a CI check that they're current.
- [ ] **CI (GitHub Actions):** backend lint + fast tests (SQLite + Postgres matrix), frontend lint/typecheck/test/build, and docker build. Models-marked tests are a manual/nightly workflow.
- [ ] **E2E smoke:** Playwright test (login → upload synthetic video → see verdict) against the compose stack, in CI.
- [ ] **Legacy removal:** delete `app.py`, `requirements.txt`, `packages.txt`, the root `package.json` (or make it a workspace runner), and the legacy `/analyze` + `/results` endpoints (or keep them behind `VMS_ENABLE_LEGACY_API` if integrations still use them; ask the user).
- [ ] **Docs:** `docs/DEPLOY.md` (install, backup/restore Postgres + data volume, upgrade/migrate, scaling workers, GPU notes), an updated README with architecture diagram and screenshots, and `docs/API.md` pointing at `/docs` with auth examples.

## Acceptance criteria

1. On a clean machine with Docker: `cp .env.example .env && docker compose up -d && docker compose exec api python -m vms.cli create-admin …` gives a working app at `http://localhost`.
2. CI is green on a PR. The E2E smoke passes.
3. `security-review` findings are fixed or recorded with a justification.
4. No legacy entry points remain unless the user chose to keep them.

## Handoff notes

Final status. Mark the project v1.0 in PROGRESS.md, list remaining backlog ideas (S3 storage, SSO, mobile capture app, live-camera ingest, multi-tenant).
