# PROGRESS.md — Project State & Handoff Log

> **Every session:** read this after CLAUDE.md. **Before ending a session:** update the status table, tick tasks, add a session log entry, record decisions and known issues, and write handoff notes. The next session has no other memory.

## Current phase: **Phase 1 — Analysis engine v2** (not started; Phase 0 done)

## Phase status

| # | Phase | Spec | Status | Branch | Completed |
|---|---|---|---|---|---|
| — | Codebase analysis & planning | this file, IMPLEMENTATION.md | ✅ done | `main` | 2026-10-01 |
| 0 | Foundation & cleanup | [PHASE_0](docs/phases/PHASE_0_foundation.md) | ✅ done | `phase-0-foundation` | 2026-10-01 |
| 1 | Analysis engine v2 | [PHASE_1](docs/phases/PHASE_1_analysis_engine.md) | ⏳ next | `phase-1-analysis-engine` | |
| 2 | Data layer, jobs, API v1 | [PHASE_2](docs/phases/PHASE_2_data_jobs_api.md) | ⬜ | `phase-2-data-jobs-api` | |
| 3 | Auth, roles, audit | [PHASE_3](docs/phases/PHASE_3_auth_users.md) | ⬜ | `phase-3-auth-users` | |
| 4 | Web frontend (core) | [PHASE_4](docs/phases/PHASE_4_frontend.md) | ⬜ | `phase-4-frontend` | |
| 5 | Review workflow, reports, admin | [PHASE_5](docs/phases/PHASE_5_review_reports_admin.md) | ⬜ | `phase-5-review-reports-admin` | |
| 6 | ML training & evaluation | [PHASE_6](docs/phases/PHASE_6_ml_training_eval.md) | ⬜ | `phase-6-ml` | |
| 7 | Production hardening & deploy | [PHASE_7](docs/phases/PHASE_7_production.md) | ⬜ | `phase-7-production` | |

Legend: ⬜ not started · ⏳ next / in progress · ✅ done · ⚠️ done with caveats (see Known issues)

Dependencies: 0 → 1 → 2 → 3 → 4 → 5. Phase 6 needs 1 and 2 (it's better after 5, when human reviews exist). Phase 7 comes last.

## Baseline (recorded 2026-10-01, commit `4973c0d`)

- Python 3.13.2 on Windows 11. All requirements import fine (`cv2, numpy, easyocr, ultralytics, pyzbar, fastapi, streamlit`).
- `pytest test_vms_sop_analyzer.py`: **3 passed, 1 failed** (18 s). `test_empty_video_returns_zero_pointers` fails because an empty video scores 5 (free step-4 points) and the test also expects `metrics.direction_changes`, which the latest rewrite removed.
- Untracked: `yolov8n.pt` (COCO weights, auto-downloaded) and `audit_results.db` (legacy results; **keep it**, Phase 2 imports it).

## Current-phase task checklist

Copy the task list from the current phase doc here at session start, and tick items as you go.

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
| 2026-10-01 | 0 | `pct_*` use quality-valid frames as denominator; `confidence` quality ratio still uses all sampled frames | Spec fix; quality failures are penalised via confidence instead. |
| 2026-10-01 | 0 | Motion metrics (optical flow) computed on **all** sampled frames, including low-quality ones | Matches the old analyzer; rotation is still visible in blurry frames. |
| 2026-10-01 | 0 | `/analyze` streams uploads to a temp dir in 1 MB chunks and returns 413 above `VMS_MAX_UPLOAD_MB` | Avoids reading whole videos into memory (cheap, no contract change). |
| 2026-10-01 | 0 | Legacy store uses `VMS_DB_URL` (must be `sqlite:///`), default `sqlite:///audit_results.db` | Phase 2 replaces it with SQLAlchemy using the same setting. |
| 2026-10-01 | 0 | Ruff B008 allows `fastapi.Depends/File/Form/Query` | Standard FastAPI idiom. |

## Open questions for the user (from IMPLEMENTATION.md §11)

1. Is there an official SOP document? — _unanswered_
2. Real sample videos plus a human-labeled eval set for Phase 6? — _unanswered_
3. GPU in production? — _unanswered_
4. Deploy target, storage (S3?), retention period? — _unanswered_
5. Integrations and webhooks? Keep the legacy `/analyze` endpoint? — _unanswered_

## Known issues / tech debt

- `process_type` still doesn't affect scoring; YOLO singleton exists but the analyzer doesn't use it; `estimated_sides` is computed but not scored. → Phase 1.
- Fixed in Phase 0: models loading at import, OCR cadence, free +5, hard-coded sides.
- `app.py` is not covered by ruff (legacy, retired in Phase 7).
- FastAPI's TestClient emits a Starlette deprecation warning about `httpx` (harmless).
- (baseline) The Streamlit app doesn't persist results. The API is synchronous and reads uploads into memory. → Phases 2 and 4.

## Session log

### 2026-10-01 — Planning session
- Analyzed the codebase (see IMPLEMENTATION.md §2). Recorded the test baseline.
- Created CLAUDE.md, IMPLEMENTATION.md, PROGRESS.md, PROMPTS.md, and docs/phases/PHASE_0..7.
- No code changes.

### 2026-10-01 — Phase 0 session
- Baseline confirmed (3 passed, 1 failed). Branch `phase-0-foundation`.
- Restructured into `backend/vms`, added settings, lazy detectors, bug fixes, and the pytest suite (16 fast tests, ~10 s, no ML libs needed).
- `pytest -m models`: 1 passed (~11 s). Streamlit app loads without errors.
- Smoke-tested `uvicorn vms.api.main:app` live: `/health` OK, `/analyze` returns the v1 shape with `direction_changes`.

## Handoff notes for next session

**Start Phase 1.** State after Phase 0:
- Layout: `backend/vms/{config.py, logging.py, legacy_store.py, analysis/{legacy_analyzer.py, detectors/{ocr,yolo}.py}, api/main.py}`, `backend/tests/{conftest.py, fixtures/video_factory.py, test_*.py}`, `ml/extract_frames.py`. Streamlit `app.py` is still at the root.
- Setup: `py -m venv .venv`, then `pip install -e "backend[dev]"` (add `,ml` for EasyOCR/YOLO). Tests: `pytest backend/tests -q` (fast, ~10 s) and `pytest backend/tests -q -m models`.
- `conftest.py` autouse fixture: points `VMS_DB_URL`/`VMS_DATA_DIR` at tmp_path and disables OCR/YOLO for all tests not marked `models`. It clears the `get_settings`/`get_ocr_reader`/`get_yolo` caches around each test, so any new cached singleton must be cleared there too.
- Detectors: `get_ocr_reader()` / `get_yolo()` (lru_cache) return `None` when disabled (`VMS_OCR_ENABLED`/`VMS_YOLO_ENABLED`) or not installed. Phase 1 should grow `detectors/` into the `base.py` protocol plus modules per IMPLEMENTATION.md §4 and reuse these singletons.
- Motion logic lives in `VMSSOPAnalyzer._detect_rotation_direction` and `_rotation_metrics`. Move it to `detectors/motion.py` when building the pipeline.
- `test_package.py` checks in a subprocess that importing `vms`, `vms.analysis.legacy_analyzer`, and `vms.api.main` doesn't load easyocr/ultralytics/torch. Keep new modules lazy.
- Python 3.13 / ML deps: `pip install -e "backend[dev,ml]"` installed cleanly on 3.13.2 (torch 2.14.1 CPU, easyocr 1.7.2, ultralytics 8.4.171, ~5 min download). No pinning needed. `pytest -m models` (1 test, real EasyOCR) takes ~11 s. EasyOCR downloads its weights on first use.
- Streamlit verified headless via `streamlit.testing.v1.AppTest` (no exceptions) and `streamlit run app.py` serves `/_stcore/health`.
