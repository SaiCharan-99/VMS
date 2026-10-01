# PROGRESS.md — Project State & Handoff Log

> **Every session:** read this after CLAUDE.md. **Before ending a session:** update the status table, tick tasks, add a session log entry, record decisions and known issues, and write handoff notes. The next session has no other memory.

## Current phase: **Phase 6 — ML training & evaluation** (not started; Phase 5 done)

## Phase status

| # | Phase | Spec | Status | Branch | Completed |
|---|---|---|---|---|---|
| — | Codebase analysis & planning | this file, IMPLEMENTATION.md | ✅ done | `main` | 2026-10-01 |
| 0 | Foundation & cleanup | [PHASE_0](docs/phases/PHASE_0_foundation.md) | ✅ done | `phase-0-foundation` | 2026-10-01 |
| 1 | Analysis engine v2 | [PHASE_1](docs/phases/PHASE_1_analysis_engine.md) | ✅ done | `phase-1-analysis-engine` | 2026-10-01 |
| 2 | Data layer, jobs, API v1 | [PHASE_2](docs/phases/PHASE_2_data_jobs_api.md) | ✅ done | `phase-2-data-jobs-api` | 2026-10-01 |
| 3 | Auth, roles, audit | [PHASE_3](docs/phases/PHASE_3_auth_users.md) | ✅ done | `phase-3-auth-users` | 2026-10-01 |
| 4 | Web frontend (core) | [PHASE_4](docs/phases/PHASE_4_frontend.md) | ✅ done | `phase-4-frontend` | 2026-10-01 |
| 5 | Review workflow, reports, admin | [PHASE_5](docs/phases/PHASE_5_review_reports_admin.md) | ⚠️ done (PDF report skipped) | `phase-5-review-reports-admin` | 2026-10-01 |
| 6 | ML training & evaluation | [PHASE_6](docs/phases/PHASE_6_ml_training_eval.md) | ⏳ next | `phase-6-ml` | |
| 7 | Production hardening & deploy | [PHASE_7](docs/phases/PHASE_7_production.md) | ⬜ | `phase-7-production` | |

Legend: ⬜ not started · ⏳ next / in progress · ✅ done · ⚠️ done with caveats (see Known issues)

Dependencies: 0 → 1 → 2 → 3 → 4 → 5. Phase 6 needs 1 and 2 (it's better after 5, when human reviews exist). Phase 7 comes last.

## Baseline (recorded 2026-10-01, commit `4973c0d`)

- Python 3.13.2 on Windows 11. All requirements import fine (`cv2, numpy, easyocr, ultralytics, pyzbar, fastapi, streamlit`).
- `pytest test_vms_sop_analyzer.py`: **3 passed, 1 failed** (18 s). `test_empty_video_returns_zero_pointers` fails because an empty video scores 5 (free step-4 points) and the test also expects `metrics.direction_changes`, which the latest rewrite removed.
- Untracked: `yolov8n.pt` (COCO weights, auto-downloaded) and `audit_results.db` (legacy results; **keep it**, Phase 2 imports it).

## Current-phase task checklist

Copy the task list from the current phase doc here at session start, and tick items as you go.

Phase 5 (done except the stretch PDF):
- [x] `services/reviews.py`: pass/fail + reason code (§7 list) + comment; comment required for `other` or when overturning a model pass/fail; append-only, latest wins via `refresh_final_status`; audit `review.created` (model status, decision, reason, comment)
- [x] `GET /review-queue` (oldest first, `process_type`/`station_id`), `POST /videos/{id}/reviews`; `GET /videos/{id}` reviews carry `reviewer_name`; `VideoOut.human_reviewed`
- [x] `services/reports.py` + `GET /reports/summary` (totals, pass rate, review rate, agreement, avg score, avg turnaround, top failed checks from `result_json`, groups by day/station/operator/process_type; tz-aware local days)
- [x] `GET /reports/export.csv`: Streamlit columns + AWB, Station, Operator, Final Status, Reviewer, Review Reason, Review Comment; UTF-8 BOM; streamed in 500-video batches on its own session
- [ ] `GET /videos/{id}/report.pdf`: **skipped (stretch goal)**; no PDF library added
- [x] Backend tests: `test_reviews.py` (11), `test_reports.py` (8, hand-calculated fixture `tests/report_fixture.py`), `test_sop_doc.py` (2), role matrix +4 routes (20 cases). Suite **293 passed**
- [x] `/review`: queue list + focused `InspectionView` + sticky `ReviewBar`; keys 1–7 reason, P/F decide, N next, J/K ±5 s, Esc leaves a field; optimistic advance with rollback on error; nav badge with the queue size
- [x] Review history on `/videos/:id` (`ReviewHistory`); human-override icon in lists (`StatusBadge human`)
- [x] `/reports`: 7/30/90/custom range, type + station filters, 4 KPI tiles, stacked status-per-day chart (Recharts) + table view, top failed checks, station/operator breakdown, CSV export (also on Inspections for reviewer+)
- [x] Dashboard (reviewer+): from `/reports/summary`: today's count, pass rate + 7-day sparkline, awaiting review, agreement; 7-day outcome chart; most-missed checks. Operators keep the list-count tiles
- [x] `/admin`: tabs Users (create; edit role/warehouse/active; reset password), Warehouses & Stations (create), API keys (create → shown once + copy; revoke with confirm), Audit log (action prefix, entity id, dates, paging)
- [x] `docs/SOP.md` generated from the rubric YAML (`python -m vms.cli sop-doc --out docs/SOP.md`; a test fails when it's stale)
- [x] Frontend tests: `phase5.test.tsx` (8: keyboard review flow, reason/comment guards, empty queue, history, reports, admin create user, tab keys). 26 frontend tests total
- [x] Acceptance 1–6 verified (see session log)

Phase 4 (all done):
- [x] Scaffold `frontend/`: Vite 6 + React 18 + TS strict, Tailwind 3, React Router 6, TanStack Query 5, zod, ESLint 9 (+jsx-a11y) + Prettier, Vitest + Testing Library + MSW. Proxy `/api` → :8000
- [x] Tokens (`src/styles/tokens.css`, light + dark), Tailwind theme mapped to tokens, Inter + JetBrains Mono (@fontsource), lucide-react; primitives in `src/components/ui/`; dev-only `/_ui` gallery
- [x] `src/api/client.ts` (VITE_API_URL, bearer, 401 → logout + redirect, typed `ApiError`, zod validation, XHR upload with progress); `src/types/analysis.ts` (§5) + `api.ts`
- [x] Auth: `/login`, token in memory + localStorage (try/catch), `AuthProvider`, `RequireRole`, role-filtered nav
- [x] App shell (232px sidebar, top bar with AWB search, theme toggle, Upload); responsive to 375px
- [x] `/upload`: drag-and-drop multi-file, Forward/Return, station, AWB, order ref, ≤2 concurrent XHR uploads, job polling every 2 s → result badge + link, compression tips
- [x] `/videos`: status/type/date/search filters synced to the URL, pagination, badges
- [x] `/videos/:id`: player (Space, J/K), evidence timeline (click → seek), verdict card, step cards with checks/details/evidence thumbnails, barcodes + quality, Re-analyze (reviewer+), pending/failed/legacy states
- [x] `/` dashboard v1: today's counts, pass rate, awaiting review, analyzing now, recent uploads
- [x] Empty / loading (skeletons) / error (Retry) states
- [x] Backend: signed media URLs, `GET /stations`, `uploaded_by_name` (rubrics + CORS already existed)
- [x] Tests: StepCard, StatusBadge (verdict), upload queue reducer, API client errors, VideosPage + VideoDetailPage with MSW (18 frontend tests); backend 252 passed
- [x] CLAUDE.md commands + README updated; Streamlit marked deprecated
- [x] Acceptance 1–5 verified (see session log)

Phase 3 (all done):
- [x] Deps: pyjwt, argon2-cffi
- [x] Settings: `env` (dev), `jwt_secret` (required, ≥32 chars, outside dev; dev auto-generates + warns), `jwt_ttl_hours` (12), `login_max_failures` (10), `login_window_s` (900)
- [x] `vms/security.py` (argon2, JWT, API-key sha256); `services/users.py`, `services/api_keys.py`, `services/principal.py`, `services/demo.py`
- [x] `deps.get_current_principal` (Bearer JWT or `X-API-Key`), `require_role`, `any_role` / `reviewer_up` / `admin_only`, `require_user`, `require_api_key`; inactive → 401
- [x] Routers `auth` (login, me, change-password) and `admin` (users, warehouses, stations, api-keys, audit-log)
- [x] Guards on every route per §8; operator + API-key isolation (403 on others' video/stream/job/evidence)
- [x] Audit: `auth.login`, `auth.login_failed`, `video.*`, `user.created/updated/deactivated/password_changed`, `warehouse.created`, `station.created`, `api_key.created/revoked` (reviews come with Phase 5)
- [x] System-admin stub removed; `system` user kept (no password, can't log in)
- [x] CLI `create-admin`, `seed-demo` (dev only, idempotent)
- [x] Login rate limit (in-memory) → 429
- [x] Tests: `test_auth.py` (23) + `test_role_matrix.py` (27 routes × 5 callers + a coverage check). Suite: 244 passed
- [x] Acceptance 1–4 verified (see session log)

Phase 2 (all done):
- [x] Deps: sqlalchemy, alembic in core; `[postgres]` extra (psycopg[binary])
- [x] `vms/db/` models for all §7 tables (+ `videos.deleted_at`, `analyses.barcodes`), engine/session (SQLite WAL, busy timeout), `seed()` system admin
- [x] Alembic (`backend/alembic.ini`, env reads settings) + `0001` initial migration that seeds the system admin; a test runs upgrade/downgrade on an empty DB
- [x] `vms/storage.py` `Storage` protocol + `LocalStorage` (atomic `.part` writes, size limit, key validation)
- [x] Services: `videos.create_from_upload` (stream, hash, dedupe, OpenCV probe, enqueue), `jobs.claim_next/heartbeat/complete/fail/release/requeue_stale`, `analyses.save_result`, `audit.log`, `legacy_import`
- [x] `python -m vms.worker [--once] [--poll]`: stale requeue, claim, throttled progress heartbeats, graceful SIGINT/SIGTERM/SIGBREAK (job released back to queue)
- [x] API: `create_app()`, routers health/videos/jobs/evidence/rubrics/legacy, stubbed `get_current_user`, Range streaming, CORS, filters + pagination + sort
- [x] AWB filled from the first barcode when empty
- [x] `python -m vms.cli import-legacy --db audit_results.db` (idempotent)
- [x] `vms/legacy_store.py` removed
- [x] Tests (85 fast): storage, migration, job queue (4-thread claim race, stale → requeue → failed, lost ownership, release), upload → worker → result, dedupe, 413, 400, corrupt → failed, shutdown release, filters/pagination, Range 206, reanalyze/delete, 404s, rubrics, OpenAPI paths, legacy `/analyze` + `/results`, legacy import
- [x] Acceptance 1–4 verified live (see session log)

Phase 1 (all done):
- [x] `result.py` (schema 2.0 Pydantic models + `to_v1()`)
- [x] `rubric.py` (load/validate YAML, `evaluate`, `decide` + caps); `forward-v1.yaml`, `return-v1.yaml`
- [x] `sampling.py`, `detectors/{base,quality,motion,objects,heuristics,barcode,ocr}.py`, `metrics.py`, `confidence.py`, `evidence.py`, `summary.py`, `pipeline.py`
- [x] Barcode: all distinct codes with `first_seen_s` / `frames_seen`; variants original → equalized → 2× upscale → adaptive; expensive variants skipped once a code is seen 3×
- [x] OCR every `ocr_every_n` valid frames + on label onset; `timings_ms` recorded (per detector too)
- [x] `python -m vms.cli analyze <video> --process-type … [--json] [--evidence-dir] [--no-evidence]`
- [x] `app.py` renders steps/titles/descriptions from the rubric via the v2 result
- [x] Tests: rubric (weights, every op, partial tiers, caps downgrade-only, unknown metric, YAML threshold change), metrics on hand-built signals, pipeline on synthetic videos (QR, dark, blur, short, empty, moving box, Forward vs Return, determinism, evidence, progress, OCR cadence), `to_v1()` keys
- [x] Acceptance 1–5 checked (see session log)

Phase 0 (all done):
- [x] Repo hygiene: `.gitignore` extended; `yolov8n.pt` / `audit_results.db` kept on disk, ignored
- [x] `backend/pyproject.toml` (core deps, `[ml]`, `[dev]`, ruff + pytest config)
- [x] `vms/config.py` Settings + `get_settings()` (lru_cache)
- [x] `vms/logging.py` `configure_logging()` (called by the API entry point only)
- [x] Analyzer → `vms/analysis/legacy_analyzer.py`; lazy `get_ocr_reader()` / `get_yolo()` in `vms/analysis/detectors/`
- [x] Bug fixes: OCR cadence by sample index; free +5 removed (product visibility = 25); `pct_*` over valid frames; `direction_changes` + `estimated_sides` restored (0 for empty video)
- [x] `server.py` → `vms/api/main.py`; `audit_store.py` → `vms/legacy_store.py` (path from `VMS_DB_URL`)
- [x] `extract_frames.py` → `ml/extract_frames.py` (pathlib)
- [x] `app.py` imports `vms.analysis.legacy_analyzer`, misindented block fixed; `requirements.txt` = `-e ./backend[ml]` + streamlit + pandas; `package.json` scripts updated
- [x] Tests in `backend/tests/` (video_factory, 4 ported + 12 new, 1 `models` test)
- [x] ruff check / format clean
- [x] README quickstart rewritten

## Decisions log

| Date | Phase | Decision | Reason |
|---|---|---|---|
| 2026-10-01 | plan | Backend: FastAPI + SQLAlchemy 2 + Alembic. SQLite dev, Postgres prod. | Already on FastAPI. The same code works on both DBs. |
| 2026-10-01 | plan | Job queue = DB table + polling worker (no Redis/Celery) | Simple Windows dev. Low-volume, slow CV jobs. |
| 2026-10-01 | plan | Frontend = React + Vite + TS. Streamlit is retired in Phase 7. | A multi-page app with a reviewer workflow, auth, and an evidence player is beyond Streamlit. |
| 2026-10-01 | plan | Scoring rules live in versioned YAML rubrics. Results use versioned schema 2.0. | Thresholds change often. Historical results must stay explainable. |
| 2026-10-01 | plan | Review-first hard caps: no barcode or poor quality → never `pass` | The product principle in the README. |
| 2026-10-01 | plan | Rubric content inferred from `app.py` text | No official SOP doc yet (Open Question 1). |
| 2026-10-01 | plan | Clean UI: light-first neutral design + dark mode, one blue accent, status colours reserved for pass/review/fail. Spec in `docs/UI_DESIGN.md`, visual target `docs/ui/mockup.html`. Supersedes the Streamlit dark look. | User asked for a clean UI. |
| 2026-10-01 | 0 | `pct_*` use quality-valid frames as denominator; `confidence` quality ratio still uses all sampled frames | Spec fix; quality failures are penalised via confidence instead. |
| 2026-10-01 | 0 | Motion metrics (optical flow) computed on **all** sampled frames, including low-quality ones | Matches the old analyzer; rotation is still visible in blurry frames. |
| 2026-10-01 | 0 | `/analyze` streams uploads to a temp dir in 1 MB chunks and returns 413 above `VMS_MAX_UPLOAD_MB` | Avoids reading whole videos into memory (cheap, no contract change). |
| 2026-10-01 | 0 | Legacy store uses `VMS_DB_URL` (must be `sqlite:///`), default `sqlite:///audit_results.db` | Phase 2 replaces it with SQLAlchemy using the same setting. |
| 2026-10-01 | 0 | Ruff B008 allows `fastapi.Depends/File/Form/Query` | Standard FastAPI idiom. |

| 2026-10-01 | 1 | Branched `phase-1-analysis-engine` from `phase-0-foundation` (not `main`) | Phase 0 isn't merged into `main` yet. |
| 2026-10-01 | 1 | Rubric checks keep the v1 operators (`>` where v1 used `>`), not the `>=` in the §6 example | "Carry over the current thresholds" exactly. |
| 2026-10-01 | 1 | Step 1 gained `label_held` (`max_label_hold_s >= 2`, 5 pts, taken from `label_text_visible` 15→10). Return step 4 = `product_visible` 20 + `product_turned` (`direction_changes >= 2`, partial ≥1 → 2) 5. Forward step 2 = package 8 + `sealing_motion` (`end_activity_ratio >= 0.3`) 6 + duration 6. | Uses min hold, "both sides shown", and "sealing near the end" as the phase doc asks; weights stay 30/20/25/25. |
| 2026-10-01 | 1 | `min_hold_sec` removed from `VMSSOPAnalyzer` and the Streamlit slider; the hold threshold lives in the rubric YAML | Thresholds belong in YAML, not code or UI. |
| 2026-10-01 | 1 | OCR uses EasyOCR **text detection only** (`reader.detect`) on a 480-wide copy (`VMS_OCR_WIDTH`). Extra OCR runs on label **onset**, not on every label frame. | Only the box count is scored. The label heuristic fires on ~every frame, so "every label frame" meant OCR on all frames (142 s for a 60 s video). Detect at 480 ≈ 0.40 s vs 0.70 s at 640. |
| 2026-10-01 | 1 | Dark threshold raised: valid frames need brightness in `[VMS_MIN_BRIGHTNESS=40, VMS_MAX_BRIGHTNESS=250]` (v1: 10–255) | v1 accepted nearly black frames as valid. |
| 2026-10-01 | 1 | YOLO adds product/package flags via `VMS_YOLO_CLASS_MAP`; the contour heuristic still counts as product while `VMS_HEURISTIC_PRODUCT_FALLBACK=true` (default) | COCO has no apparel classes, so without the fallback no real video could score step 4. Turn it off once the Phase 6 model ships. |
| 2026-10-01 | 1 | `caps_applied` lists only caps that actually lowered the status. A cap whose metric is missing applies. | Clear audit meaning; review-first. |
| 2026-10-01 | 1 | Metrics added beyond §5: `barcode_count`, `end_activity_ratio`, `quality_ok_ratio`, `frames_sampled`. The evidence path rule and per-detector timings are documented in IMPLEMENTATION.md §5. | Needed by rubrics and caps; contract documented. |

| 2026-10-01 | 2 | Branched `phase-2-data-jobs-api` from `phase-1-analysis-engine` | Phases 0/1 still aren't merged into `main`. |
| 2026-10-01 | 2 | Schema additions to §7: `videos.deleted_at` (soft delete), `analyses.barcodes` (space-joined values for `q` search), `analyses.job_id` nullable (legacy imports), `videos.sha256` indexed but not unique. Enums are strings + CHECK constraints. Timestamps are naive UTC, serialized with `Z`. | Documented in IMPLEMENTATION.md §7. Avoids native Postgres enums and JSON-text search. |
| 2026-10-01 | 2 | A duplicate upload returns **200** `{video, job, duplicate: true}` (a new upload returns 201) | Nothing was created, so 201 would be misleading. |
| 2026-10-01 | 2 | Analysis exceptions fail the job at once (no retry). `max_attempts` only bounds stale/lost-worker retries. | A corrupt video fails the same way every time. |
| 2026-10-01 | 2 | Graceful shutdown releases the running job back to `queued` without counting the attempt, and deletes partial evidence | Restarting a worker shouldn't burn attempts. |
| 2026-10-01 | 2 | Legacy `POST /analyze` stores the upload (`source=api`) and runs the job inline (`worker_id api-sync:*`, `max_attempts=1`). `GET /results` reads `analyses` (row `id` = analysis id, `result_json` = v1 JSON). | The phase doc says the legacy routes read the new tables. |
| 2026-10-01 | 2 | The pipeline writes evidence JPEGs straight to `storage.path("evidence/<uuid>")` | Works for `LocalStorage` only. An S3 backend will need an upload step after analysis. |
| 2026-10-01 | 2 | Layout deviations from §4: no `db/base.py` (Base lives in `models.py`), `api/schemas.py` is one module, `api/views.py` holds ORM → response helpers, and there are extra routers `evidence.py` and `rubrics.py`. Also implemented `POST /videos/{id}/reanalyze` and soft `DELETE /videos/{id}` (role checks come in Phase 3). | Small modules. These endpoints were trivial once the services existed. |
| 2026-10-01 | 2 | The default `VMS_DB_URL` is now `sqlite:///data/vms.db`. `audit_results.db` is only read by `import-legacy`. | The new schema lives under `data/`. |

| 2026-10-01 | 3 | Branched `phase-3-auth-users` from `phase-2-data-jobs-api` | Earlier phases still aren't merged into `main`. |
| 2026-10-01 | 3 | Migration `0002` adds `videos.api_key_id` (FK, indexed) | An API key acts as an operator; isolation needs to know which key uploaded what (`uploaded_by` is NULL for key uploads). |
| 2026-10-01 | 3 | Legacy `POST /analyze` / `GET /results` accept **API keys only** (JWT users get 403), and `/results` lists only that key's uploads | §8 says "api key"; operator-style isolation. Imported legacy rows are visible to reviewers/admins via `/api/v1/videos`. |
| 2026-10-01 | 3 | `/auth/me` and `/auth/change-password` need a user (API key → 403) | An API key has no profile. |
| 2026-10-01 | 3 | The JWT carries only `sub` + `exp`/`iat`; role and `is_active` are read from the DB on every request | Role changes and deactivation take effect immediately. |
| 2026-10-01 | 3 | API keys: `vms_` + 32 random bytes, stored as sha256 (not argon2) | High-entropy keys; a fast hash allows lookup by hash. |
| 2026-10-01 | 3 | Admin can't demote or deactivate themselves (400) | Avoids locking out the last admin. |
| 2026-10-01 | 3 | Upload with an unknown `station_id` → 400 (was a FK 500) | Small fix while touching the route. |
| 2026-10-01 | 3 | Role-matrix coverage reads routes from OpenAPI (+ hidden root `/health`) | FastAPI 0.142 nests included routers (`_IncludedRouter`), so `app.routes` has no `APIRoute`s. |
| 2026-10-01 | 4 | Branched `phase-4-frontend` from `phase-3-auth-users` | Earlier phases still aren't merged into `main`. |
| 2026-10-01 | 4 | Media auth = **signed URLs**: `stream_url` and evidence `url` carry `?exp=&sig=` (HMAC-SHA256 of path+exp with the JWT secret, TTL `VMS_MEDIA_URL_TTL_S` = 6 h). `deps.media_access` accepts a valid signature or normal auth. | `<video>`/`<img>` can't send headers; blob-fetching 500 MB videos breaks Range seeking. A URL only works for the path it was issued for. After 6 h on one page, reload. |
| 2026-10-01 | 4 | Added `GET /api/v1/stations` (any role) and `VideoOut.uploaded_by_name` | Operators can't call `/admin/stations`; the Inspections table needs an operator name. Additive, no schema bump. |
| 2026-10-01 | 4 | Token contrast deviations from UI_DESIGN §2: `--text-3` light `#5f6b7e` (spec `#98a2b3`), dark `#8a93a1` (spec `#6b7380`); light `--pass` `#0f7654` (spec `#12805c`, 4.41:1 on pass-soft); new `--on-accent`/`--on-status` (white in light, `#0c0e12` in dark, since white on `#6b8cff` is ~3:1) | WCAG AA text contrast (acceptance 5). |
| 2026-10-01 | 4 | Breakpoints remapped: `md` = 760px, `lg` = 1000px. Top-bar search shows from 1000px (at 768 it squeezed out the page title). Upload rows use 3 columns only from 1280px. | Spec §3 breakpoints; no horizontal scroll at 375/768/1366. |
| 2026-10-01 | 4 | Not built yet (Phase 5): Review queue / Reports / Admin nav items, charts, Export CSV, Download report, station filter on Inspections. Dashboard tile 4 is "Analyzing now" instead of model–reviewer agreement. Table thumbnails are a placeholder icon. | Out of scope or no backend yet. |
| 2026-10-01 | 4 | Dashboard counts use `GET /videos?page_size=1` totals (one call per status) | No summary endpoint until `/reports/summary` (Phase 5). |
| 2026-10-01 | 4 | Coincident evidence markers fan out 16px apart | Synthetic videos put every step's evidence at the same second. |
| 2026-10-01 | 5 | Branched `phase-5-review-reports-admin` from `phase-4-frontend` | Earlier phases still aren't merged into `main`. |
| 2026-10-01 | 5 | Tests ignore the developer `.env` (`Settings.model_config["env_file"] = None` in conftest) | Baseline was red: a local `VMS_JWT_SECRET` in `.env` defeated `test_jwt_secret_required_outside_dev`. |
| 2026-10-01 | 5 | Report aggregation runs in Python over one row per video (no `analysis_checks` table, no JSON SQL) | Same code on SQLite and Postgres; volumes are small. Revisit (precomputed table) if ranges reach ~100k videos. |
| 2026-10-01 | 5 | KPI definitions: pass_rate = final pass / analyzed (final ≠ pending); review_rate = latest *model* status review / analyzed; agreement = over reviewed videos whose *judged* analysis said pass/fail, the share where the human matched (model `review` is excluded because it abstained); turnaround = upload → latest review, or → analysis when the model settled it, over final pass/fail | Documented in `reports.summarize()` and IMPLEMENTATION.md §8. |
| 2026-10-01 | 5 | Days are the user's local days: `tz_offset_min` on `/reports/*` (the frontend sends `-getTimezoneOffset()`). The reviewer dashboard uses `/reports/summary` | Fixes the Phase 4 "today vs UTC" issue for reviewers and admins. |
| 2026-10-01 | 5 | The review comment rule is enforced server-side (422) and mirrored in the UI. Reviews need a user (API keys can't review) | Every overturn of the model is explained in the audit trail. |
| 2026-10-01 | 5 | Review keyboard: digits 1–7 pick the reason (order of the §7 list), P/F decide, N next, J/K seek, Esc leaves a field. Shortcuts are ignored while a field has focus | Without reason keys, a keyboard-only reviewer would have to tab into the select every time. |
| 2026-10-01 | 5 | Optimistic advance: the item leaves the queue cache at once; on an API error it's restored and re-selected with the draft and the message | Phase doc "optimistic advance". |
| 2026-10-01 | 5 | Charts: Recharts 2, colours resolved from CSS tokens at runtime (`useTokens`, re-read on theme change). Status series use the reserved status tokens. The dataviz validator FAILS light review vs fail for CVD (ΔE 2.4), so review segments are **hatched**, with a legend, 2px surface gaps, tooltips, and "View as table". Top failed checks are accent HTML bars (long labels) | Status colours are reserved and can't be re-stepped; secondary encoding is the dataviz-skill remedy. |
| 2026-10-01 | 5 | Extracted `InspectionView` (player + timeline + verdict + steps), shared by the detail and review pages. New primitives `Tabs` (+ `Field`); `KpiTile` takes children (sparkline); the `VideoPlayer` handle gained `skip(dt)`, and the player stops Space/J/K from propagating | Reuse instead of duplicating the detail page. |
| 2026-10-01 | 5 | Toasts moved from bottom-right to top-right under the header | They covered the sticky ReviewBar's Fail/Pass buttons during rapid reviewing. |
| 2026-10-01 | 5 | `docs/SOP.md` is generated (`vms/sop_doc.py`). Plain wording per check lives in `WHAT_IT_LOOKS_FOR`; thresholds and fail notes come from the YAML | Keeps the operator guide in sync with rubric versions; a test enforces it. |
| 2026-10-01 | 5 | PDF report (`/videos/{id}/report.pdf`) **not built** | Stretch goal; it would add reportlab/weasyprint. The detail page has no "Download report" button yet. |

## Open questions for the user (from IMPLEMENTATION.md §11)

1. Is there an official SOP document? — _unanswered_
2. Real sample videos plus a human-labeled eval set for Phase 6? — _unanswered_
3. GPU in production? — _unanswered_
4. Deploy target, storage (S3?), retention period? — _unanswered_
5. Integrations and webhooks? Keep the legacy `/analyze` endpoint? — _unanswered_

## Known issues / tech debt

- Phase 4: dashboard "today" uses the browser's local date, but the API compares it to UTC `created_at`. **Fixed in Phase 5 for reviewers and admins** (tz-aware `/reports/summary`). The operator tiles still use `GET /videos?date_from=` (UTC), so operators can still see counts off by a few hours around midnight. `GET /videos` could accept `tz_offset_min` too.
- Phase 5: the production JS bundle is ~820 kB (Recharts). Lazy-load `/reports`, `/review`, `/admin` (and the dashboard charts) in Phase 7.
- Phase 5: `/reports/summary` loads every video in the range into memory (max range 1 year). Fine for current volumes; precompute per-check rows if it gets slow.
- Phase 5: the review page loads at most 100 queue items (`page_size=100`); the header shows the true total.
- Phase 5: station/warehouse **edit/delete** still don't exist (admins can only create). Users can't be deleted, only deactivated (by design).
- Phase 5: no PDF report (stretch goal skipped).
- Phase 5: jsdom has no `HTMLDialogElement.showModal`, so dialog tests query with `hidden: true`.
- Phase 5: the CSV's Excel compatibility is asserted by tests (BOM, columns) but wasn't opened in a real Excel (none on the dev machine).
- Phase 4: signed media URLs expire after `VMS_MEDIA_URL_TTL_S`; a page left open longer needs a reload to keep streaming.
- Phase 4: TS types are hand-maintained (`frontend/src/types/*.ts` mirror `schemas.py` and `result.py`). Consider openapi-typescript in Phase 7.
- Phase 4: the `/_ui` gallery chunk is still emitted in production builds (the route itself is dev-only).
- Phase 4: OpenCV writes `mp4v`, which browsers can't play. Test videos for the player need H.264 (`avc1`; works on Windows via MSMF).

- Fixed in Phase 1: `process_type` now selects the rubric; YOLO is used; `estimated_sides` is scored (Return `six_sides`).
- Heuristic weaknesses for Phase 6: (a) the label / tag / package contour heuristics fire on almost any textured frame (label_ratio ≈ 1.0 on synthetic video), so they barely discriminate. (b) Motion magnitude is the **mean over the whole frame**, so small moving objects stay below `ACTIVE_MAGNITUDE` (a 60 s synthetic box gives 0 direction changes), and the left-vs-right-half direction heuristic can flip as one object crosses the centre (a monotonic 3 s move gives 2 changes). (c) The `avg_text_blocks` thresholds (>5 / >3) came from v1 `readtext` counts and haven't been re-tuned on real footage for `detect()` at 480 px. (d) The COCO class map is a stopgap.
- No real sample videos yet (`data/samples/` is empty). The timings below come from a synthetic video.
- Fixed in Phase 0: models loading at import, OCR cadence, free +5, hard-coded sides.
- `app.py` is not covered by ruff (legacy, retired in Phase 7).
- FastAPI's TestClient emits a Starlette deprecation warning about `httpx` (harmless).
- Fixed in Phase 2: the API is async (job queue) and persists everything. The Streamlit app still doesn't persist results (retired in Phase 7).
- Starlette spools multipart uploads to a temp file before the handler runs, so the size limit is enforced while copying to storage, not during the network transfer. A reverse-proxy body limit (Phase 7) should cap it earlier.
- Dedupe is check-then-insert, so two identical uploads at the same instant can both be stored. Low risk. A unique partial index on `sha256` could fix it later.
- `audit_results.db` on this machine has **0 rows**, so `import-legacy` imported nothing (it was tested with a synthetic legacy DB).
- Login rate limiting is **in-memory per process** (resets on restart, not shared across workers/instances). Phase 7 should move it to the DB/Redis or the reverse proxy.
- In dev without `VMS_JWT_SECRET`, each process makes a random secret, so tokens die on every `uvicorn --reload` restart. Set `VMS_JWT_SECRET` in `.env` to avoid re-logging in.
- Tokens aren't revoked on password change (they expire after `jwt_ttl_hours`). Deactivation does cut them off immediately.
- Station/warehouse **update/delete** endpoints don't exist yet (§8 lists only GET/POST); add in Phase 5 if the admin UI needs them.
- Stale jobs are re-queued at the start of each worker loop iteration, so nothing reaps them while every worker is busy.

## Session log

### 2026-10-01 — Phase 5 session
- Baseline: 251 passed, **1 failed** (`test_jwt_secret_required_outside_dev`, caused by a developer `.env`); fixed in conftest → 252. Branch `phase-5-review-reports-admin`.
- Backend now **293 passed**; ruff check/format clean. Frontend: typecheck, lint (0 warnings), 26 tests, and build all green.
- **Acceptance 2** (report math): `test_reports.py::test_summary_matches_hand_calculation` asserts every KPI, the top failed checks, and gap-filled day groups against the table in `tests/report_fixture.py`. Other tests cover station/operator groups, filters, a UTC+12 day shift, and the CSV.
- **Acceptance 3** (CSV): BOM and review columns asserted in `test_csv_export`. Not opened in a real Excel.
- **Live check** (built-in browser; scratch DB and data dir in the session scratchpad, API on :8001, Vite `--mode scratch` on :5174, because port 8000 was taken by another local python process, which was left alone): seeded 14 synthetic H.264 videos (MSMF), 12 in the review queue. As `reviewer@vms.local`, cleared **11 videos using only the keyboard** (reason digit + P/F, auto-advancing each time). DB check: 11 reviews, each video's final status matches, and each has a `review.created` audit row with the reviewer id and reason (**acceptance 1**). The Reports page matched a hand count (6/14 pass = 42.9%, 12/14 model review = 85.7%, agreement "—" because every reviewed verdict was a model `review`). As admin, created a new operator in Admin → Users, logged in as them (operator-only nav), and uploaded through `/upload` → "Queued for analysis" (**acceptance 4**).
- **Acceptance 6**: no raw hex in the new screens (colours via tokens; charts read tokens at runtime), and only `components/ui` primitives (plus the new `Tabs`/`Field`). `scrollWidth == innerWidth` on dashboard, review, reports, and admin (users/audit/keys) at 375 px; desktop checked in light and dark; no console errors. Found and fixed: toasts covering the ReviewBar, and an empty sparkline with only one data point.

### 2026-10-01 — Phase 4 session
- Baseline 244 passed. Branch `phase-4-frontend`. Backend now 252 passed; ruff clean.
- Frontend: `npm run build`, `npm run lint` (0 warnings), `npm test` (18 passed), `tsc --noEmit` all clean.
- **Live acceptance** (Built-in browser pane, API + worker + Vite running, `seed-demo`): logged in as `operator@vms.local`; uploaded 3 synthetic H.264 videos through the upload page (files injected into the file input, since the pane can't open the OS picker). They showed upload %, then "Analyzing N%", then badges (Review 74, Review 74, Fail 0). Opened one; the video streamed through the signed URL; clicking a timeline marker set `currentTime` to 11.33 (the evidence time). Operator: no Re-analyze (a reviewer sees it, per page test); other users' videos are blocked by the API (role matrix).
- Responsive: `scrollWidth == innerWidth` at 375, 768 and 1366 on dashboard, upload, inspections, and detail (only the mobile nav row scrolls, by design). Compared with `docs/ui/mockup.html` in light and dark; deviations listed in Decisions.
- Accessibility (`design:accessibility-review`): fixed light `--pass` and `--text-3` contrast (now ≥4.5:1 in both themes), added `prefers-reduced-motion`, skip link, labelled controls (a scan found no unlabelled controls), focus ring on every control, keyboard rows (Enter opens), player keys, and accessible names on timeline markers. Not fixed: touch targets <44px (2.5.5 is AAA, not AA).

### 2026-10-01 — Planning session
- Analyzed the codebase (see IMPLEMENTATION.md §2). Recorded the test baseline.
- Created CLAUDE.md, IMPLEMENTATION.md, PROGRESS.md, PROMPTS.md, and docs/phases/PHASE_0..7.
- No code changes.

### 2026-10-01 — Phase 0 session
- Baseline confirmed (3 passed, 1 failed). Branch `phase-0-foundation`.
- Restructured into `backend/vms`, added settings, lazy detectors, bug fixes, and the pytest suite (16 fast tests, ~10 s, no ML libs needed).
- `pytest -m models`: 1 passed (~11 s). Streamlit app loads without errors.
- Smoke-tested `uvicorn vms.api.main:app` live: `/health` OK, `/analyze` returns the v1 shape with `direction_changes`.

### 2026-10-01 — Phase 3 session
- Baseline 85 passed. Branch `phase-3-auth-users`. Installed pyjwt 2.15.1, argon2-cffi 25.1.0.
- Built auth/roles/admin/audit/CLI. Fast suite: **244 passed in ~25 s** (tests use cheap argon2 params). `ruff check` / `ruff format` clean.
- **Live acceptance** (scratch DB): `alembic upgrade head` ran 0001 → 0002; `create-admin` → login → `/auth/me` returned the admin with `last_login_at`; `seed-demo` printed the demo logins; `/api/v1/videos` without creds → 401, `/api/v1/health` → 200. Acceptance (1) and (2) are enforced by `test_role_matrix.py`.

### 2026-10-01 — Phase 2 session
- Baseline 57 passed. Branch `phase-2-data-jobs-api` (from `phase-1-analysis-engine`). Installed sqlalchemy 2.1.1 and alembic 1.20.0.
- Built db/storage/services/worker/API v1/legacy import. Fast suite: **85 passed in ~11 s**. `-m models`: 1 passed. `ruff check` / `ruff format --check` clean.
- **Live acceptance** (scratch DB, `VMS_JOB_STALE_S=10`, OCR+YOLO on, 30 s 1280×720 synthetic video): (1) `curl -F file=@x.mp4 -F process_type=Return …/api/v1/videos` → **201 in 0.30 s**. The job was polled to `done`, and `/videos/1` showed `review 60/100`, the auto-filled AWB `AWB-E2E-1`, and 4 evidence URLs serving JPEGs. A Range request returned 206. (2) The worker was hard-killed (`Stop-Process -Force`) at 33 % progress, leaving the job `running`. The restarted worker logged `Stale jobs: 1 re-queued` and reran it (attempt 2) to `done` (~25 s analysis). (3) `/docs` returned 200, and a test checks that OpenAPI lists every Phase 2 path with typed response models. (4) Tests and ruff green.
- `import-legacy` on the real `audit_results.db` found 0 rows to import (the file was opened read-only).

### 2026-10-01 — Phase 1 session
- Baseline 16 passed. Branch `phase-1-analysis-engine` (from `phase-0-foundation`).
- Built the v2 pipeline, rubrics, CLI, and tests. Fast suite: **57 passed in ~8 s**. `-m models`: 1 passed (~16 s). `ruff check` / `ruff format` clean.
- **Measured (16-thread Windows laptop, CPU only, OCR + YOLO on):** a synthetic 60 s 1280×720 30 fps video (QR + text + moving box) gives 180 sampled frames. Analysis **45.3 s**; CLI wall clock **46.8 s** including model load. Breakdown (ms): sampling 942, quality 543, motion 2128, objects (heuristics + yolov8n) 8041, barcode 1316, OCR 26996 (≈60 calls × 0.45 s), scoring 1, evidence 8. Before switching OCR to 480 px detect-only with onset triggering: 142 s.
- Acceptance: (1) the CLI writes a schema-valid result and 4 evidence JPEGs ✔. (2) `test_yaml_threshold_change_changes_score` ✔. (3) `test_shipped_caps_block_pass` plus the pipeline dark/blur tests ✔. (4) suite 8 s; 60 s video 45 s ✔. (5) `/analyze` is covered by `test_api.py` (v1 shape). `app.py` was verified headless with Streamlit AppTest and a stubbed upload in both modes (no exceptions; titles and CSV columns come from the rubric) ✔.

## Handoff notes for next session

**Start Phase 6 (ML training & evaluation).** State after Phase 5:
- Human labels now exist: `reviews` (append-only; the latest per video wins) with `reason_code` (§7) and the judged `analysis_id`. Model-vs-human pairs: join `reviews` → `analyses` on `analysis_id` (`services/reports.load_rows` already computes `reviewed_status`). `false_negative_model` means the model was wrong and the operator was compliant, which makes it the best source of corrected labels for Phase 6.
- **Numbers the phase doc asked for:** there is still **no real data** (`data/samples/` is empty, `audit_results.db` has 0 rows), so there is no meaningful agreement rate or most-failed-check ranking yet. Synthetic videos fail almost every check, which says nothing. Once real reviews exist, read `agreement_rate`/`agreement_n` and `top_failed_checks` from `GET /reports/summary` (or the Reports page) and prioritise from those.
- Reports API: `/reports/summary` (+`group_by`) and `/reports/export.csv` (same filters as `/videos`), both reviewer+, both take `tz_offset_min`. The CSV is a convenient eval-set export (per-step % + human decision + reason).
- Operator guide: `docs/SOP.md` is generated. After any rubric change (e.g. `forward-v2`), add plain wording for new check keys in `vms/sop_doc.py::WHAT_IT_LOOKS_FOR` and rerun `python -m vms.cli sop-doc --out docs/SOP.md` (a test fails otherwise). Frontend check labels live in `frontend/src/lib/copy.ts::CHECK_LABEL`.
- Frontend map additions: `src/pages/{ReviewPage,ReportsPage,AdminPage}.tsx`, `src/pages/admin/*Tab.tsx`, `src/components/inspection/InspectionView.tsx`, `src/components/review/{ReviewBar,ReviewHistory}.tsx`, `src/components/charts/{StatusByDayChart,Sparkline,FailedChecksList,useTokens}`, `src/lib/{review,tabs}.ts`, `src/components/ui/Tabs.tsx`.
- New routes must go into `MATRIX` in `backend/tests/test_role_matrix.py`.
- Live-testing tips: synthetic H.264 videos need `cv2.VideoWriter(path, cv2.CAP_MSMF, fourcc("avc1"), ...)` on Windows (the FFmpeg backend's openh264 fails). If port 8000 is busy, run the API on another port and start Vite with `VITE_API_URL` set (a gitignored `frontend/.env.<mode>.local` plus `--mode <mode>`).

### Phase 4 handoff (kept for reference)

**Start Phase 5 (review workflow, reports, admin).** State after Phase 4:
- Run: API (`uvicorn vms.api.main:app --reload --port 8000`), worker (`python -m vms.worker`), web (`cd frontend; npm run dev`, or `preview_start web` from `.claude/launch.json`). Demo logins are in the Phase 3 handoff below. `.env` needs `VMS_JWT_SECRET`.
- Frontend map: `src/api/{client,endpoints,queries,queryClient}.ts`, `src/auth/{AuthProvider,RequireRole,roles,tokenStore}`, `src/components/ui/*` (Bar, Button/IconButton, Card/CardHeader/CardBody, DataTable, Dialog, EmptyState, ErrorState, FilterBar, Kbd, KpiTile, ScoreRing, Segmented, Skeleton, StatusBadge, Toast), `src/components/inspection/{VideoPlayer,EvidenceTimeline,StepCard,VerdictCard}`, `src/components/{AppShell,UploadQueue,VideoTable}`, `src/pages/*`, `src/upload/queue.ts`. Gallery at `/_ui` (dev).
- Phase 5 to-dos in the UI: add nav items (Review queue with amber count, Reports, Admin) to `NAV` in `AppShell.tsx` with `REVIEWER_UP`/admin roles and wrap routes in `<RequireRole roles=...>`. Build `ReviewBar` (not built yet). Reuse `VideoPlayer` (`seek` handle, J/K) + `StepCard`/`VerdictCard` for the review page. `StatusBadge human` shows reviewer overrides (detail page passes `reviews.length > 0`). Swap the dashboard tile 4 to model–reviewer agreement, and add charts via the `dataviz` skill.
- Types: edit `frontend/src/types/api.ts` when adding endpoints. Responses are zod-validated, so a shape mismatch surfaces as "unexpected response" plus a console error.
- New routes must also go into `MATRIX` in `backend/tests/test_role_matrix.py`.
- Tests: `src/test/render.tsx` `renderPage(el, {path, url})` + MSW `server.use(...)`; fixtures in `src/test/fixtures.ts`.

### Phase 3 handoff (kept for reference)

**Start Phase 4 (web frontend).** State after Phase 3:
- Setup: `pip install -e "backend[dev]"` (adds pyjwt, argon2-cffi), then `alembic -c backend/alembic.ini upgrade head` (new migration `0002`). Put `VMS_JWT_SECRET=<32+ chars>` in `.env` so tokens survive reloads.
- **Demo credentials** (`python -m vms.cli seed-demo`, dev only; warehouse `DEMO`, stations `ST-1`, `ST-2`):

  | Role | Email | Password |
  |---|---|---|
  | operator | operator@vms.local | operator-demo-1 |
  | reviewer | reviewer@vms.local | reviewer-demo-1 |
  | admin | admin@vms.local | admin-demo-1 |

  Real admins: `python -m vms.cli create-admin --email … --name …` (prompts for the password).
- Login: `POST /api/v1/auth/login {email, password}` → `{access_token, token_type: "bearer", expires_in, user}`. Send `Authorization: Bearer <token>`. 401 → redirect to login; 429 → show "too many attempts". `GET /auth/me` returns `UserOut` (`id, email, name, role, warehouse_id, is_active, created_at, last_login_at`). There's no refresh token: re-login after `expires_in` (12 h).
- **Role matrix** (§8, enforced by `tests/test_role_matrix.py`): public = `/health`, `/auth/login`; any user = `/auth/me`, `/auth/change-password`; any user or API key = upload, list, video detail/stream, job, evidence, rubrics (operators and keys only their own; 403 otherwise); reviewer+ = reanalyze; admin = `DELETE /videos/{id}` and all `/admin/*`; API key only = legacy `/analyze`, `/results`. Hide UI actions by role, but rely on the API for enforcement.
- `<video>` and `<img>` tags can't send an `Authorization` header. The stream and evidence URLs need auth, so the frontend must fetch them as blobs (or Phase 4 adds a short-lived signed URL / cookie). Decide and record it.
- §8 changes: `POST /auth/change-password`, `PATCH /admin/users/{id}`, `DELETE /admin/api-keys/{id}`, `GET /admin/audit-log`; `videos.api_key_id`. Phase 5 routes (`/review-queue`, `/videos/{id}/reviews`, `/reports/*`) must use `reviewer_up` from `vms.api.deps`, log `review.created` via `audit.log(..., **principal.actor)`, call `analyses.refresh_final_status`, and be added to `MATRIX` in the role-matrix test (it fails if a route is missing).
- Tests: fixtures `client` (admin), `anon_client`, `api_client`, `make_user(role, email=None)`, `make_api_key()`, and helper `auth(user)` → headers (all in `tests/conftest.py`). Password for test users: `TEST_PASSWORD`.

### Phase 2 handoff (kept for reference)

State after Phase 2:
- Run locally (PowerShell, repo root, venv active):
  ```powershell
  pip install -e "backend[dev,ml]"
  alembic -c backend/alembic.ini upgrade head          # creates data/vms.db (+ system admin)
  uvicorn vms.api.main:app --reload --port 8000        # http://localhost:8000/docs
  python -m vms.worker                                 # 2nd terminal; Ctrl+C releases the job
  python -m vms.cli import-legacy --db audit_results.db
  curl.exe -F file=@x.mp4 -F process_type=Return localhost:8000/api/v1/videos
  ```
- New env vars (in `.env.example`): `VMS_CORS_ORIGINS`, `VMS_WORKER_POLL_S` (1.5), `VMS_JOB_STALE_S` (300), `VMS_JOB_MAX_ATTEMPTS` (3). The `VMS_DB_URL` default changed to `sqlite:///data/vms.db`. `Settings.sqlite_path` was removed.
- Auth stub: `vms.api.deps.get_current_user` returns the seeded `system@vms.local` admin (`vms.db.session.seed`). Every route already depends on it. Phase 3 replaces its body with JWT / `X-API-Key` resolution and adds role checks (`reanalyze` reviewer+, `DELETE` admin). Operators see only their own videos: `services.videos.list_query` already filters by `uploaded_by` for `Role.operator`. Upload `source` is hard-coded to `web` in `routers/videos.py`; set it to `api` for API-key callers. The legacy routes need the API-key dependency.
- The `users`, `api_keys`, `warehouses`, `stations`, `reviews`, and `audit_log` tables already exist, so Phase 3 needs no migration unless columns change. `password_hash` is nullable (the system user has none).
- `services.audit.log(session, action, entity_type, entity_id, data, actor_user_id=..., actor_api_key_id=...)` is called for `video.uploaded`, `video.deleted`, `video.reanalyze`, `analysis.completed`, `analysis.failed`, and `legacy.imported`. Worker-side entries have no actor.
- `services.analyses.refresh_final_status(session, video)` already applies "latest review wins". Call it after inserting a review (Phase 5).
- Tests: the `client` fixture (`tests/conftest.py`) builds `create_app()` on a per-test SQLite DB via `create_all()`, and `db_ready` gives just the tables. `conftest` clears the `get_engine`/`get_sessionmaker` caches (and disposes the engine) around each test, so clear any new cached singleton there too. Run the worker in tests with `Worker().run_once()`.
- Video IDs in URLs are integer ids. `uuid` is also returned.

### Phase 1 handoff (kept for reference)

**Start Phase 2.** State after Phase 1:
- Entry point: `from vms.analysis import analyze_video` → `analyze_video(path, process_type, *, settings=None, evidence_dir=None, progress_cb=None) -> AnalysisResult`. Store `result.model_dump_json()` in `analyses.result_json`. The worker should pass `evidence_dir = data_dir / "evidence" / <analysis uuid>` so image paths come out as `evidence/<uuid>/<step>_0.jpg` (relative to `VMS_DATA_DIR`).
- `progress_cb(float)` is called once per sampled frame (0..1, monotonic) and finally with 1.0.
- Errors: a missing file raises `FileNotFoundError`; an unreadable one raises `OSError`. Map both to a `failed` job.
- Rubrics: `vms.analysis.rubric.rubric_for(process_type)` / `get_rubric(id)` (cached). The legacy `/analyze` still goes through `VMSSOPAnalyzer(...).analyze()` → `AnalysisResult.to_v1()`; `routers/legacy.py` can call `analyze_video(...).to_v1()` directly.
- Metric keys: `vms.analysis.metrics.METRIC_KEYS` (table in IMPLEMENTATION.md §5).
- New settings: `VMS_ANALYSIS_WIDTH` (640), `VMS_MIN_BRIGHTNESS` (40), `VMS_MAX_BRIGHTNESS` (250), `VMS_OCR_EVERY_N` (3), `VMS_OCR_WIDTH` (480), `VMS_YOLO_CONF` (0.35), `VMS_YOLO_CLASS_MAP` (JSON), `VMS_HEURISTIC_PRODUCT_FALLBACK` (true).
- A 60 s video takes ~45 s of CPU, so the Phase 2 worker must run analyses off the request path (as planned). Load models once per worker process (the singletons already do this).
- The user's uncommitted doc edits (CLAUDE.md, PROMPTS.md, PHASE_4/5 docs, `docs/UI_DESIGN.md`, `docs/ui/`) were left uncommitted in the working tree.

### Phase 0 handoff (still relevant)


_UI note (added after Phase 0): the UI design system and mockup now exist (`docs/UI_DESIGN.md`, `docs/ui/mockup.html`). Phases 4–5 must follow them. Nothing in Phase 1 changes._

**Start Phase 1.** State after Phase 0:
- Layout: `backend/vms/{config.py, logging.py, legacy_store.py, analysis/{legacy_analyzer.py, detectors/{ocr,yolo}.py}, api/main.py}`, `backend/tests/{conftest.py, fixtures/video_factory.py, test_*.py}`, `ml/extract_frames.py`. Streamlit `app.py` is still at the root.
- Setup: `py -m venv .venv`, then `pip install -e "backend[dev]"` (add `,ml` for EasyOCR/YOLO). Tests: `pytest backend/tests -q` (fast, ~10 s) and `pytest backend/tests -q -m models`.
- `conftest.py` autouse fixture: points `VMS_DB_URL`/`VMS_DATA_DIR` at tmp_path and disables OCR/YOLO for all tests not marked `models`. It clears the `get_settings`/`get_ocr_reader`/`get_yolo` caches around each test, so any new cached singleton must be cleared there too.
- Detectors: `get_ocr_reader()` / `get_yolo()` (lru_cache) return `None` when disabled (`VMS_OCR_ENABLED`/`VMS_YOLO_ENABLED`) or not installed. Phase 1 should grow `detectors/` into the `base.py` protocol plus modules per IMPLEMENTATION.md §4 and reuse these singletons.
- Motion logic lives in `VMSSOPAnalyzer._detect_rotation_direction` and `_rotation_metrics`. Move it to `detectors/motion.py` when building the pipeline.
- `test_package.py` checks in a subprocess that importing `vms`, `vms.analysis.legacy_analyzer`, and `vms.api.main` doesn't load easyocr/ultralytics/torch. Keep new modules lazy.
- Python 3.13 / ML deps: `pip install -e "backend[dev,ml]"` installed cleanly on 3.13.2 (torch 2.14.1 CPU, easyocr 1.7.2, ultralytics 8.4.171, ~5 min download). No pinning needed. `pytest -m models` (1 test, real EasyOCR) takes ~11 s. EasyOCR downloads its weights on first use.
- Streamlit verified headless via `streamlit.testing.v1.AppTest` (no exceptions) and `streamlit run app.py` serves `/_stcore/health`.
