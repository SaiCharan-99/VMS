# PROGRESS.md — Project State & Handoff Log

> **Every session:** read this after CLAUDE.md. **Before ending a session:** update the status table, tick tasks, add a session log entry, record decisions and known issues, and write handoff notes. The next session has no other memory.

## Current phase: **Phase 0 — Foundation & Cleanup** (not started)

## Phase status

| # | Phase | Spec | Status | Branch | Completed |
|---|---|---|---|---|---|
| — | Codebase analysis & planning | this file, IMPLEMENTATION.md | ✅ done | `main` | 2026-10-01 |
| 0 | Foundation & cleanup | [PHASE_0](docs/phases/PHASE_0_foundation.md) | ⏳ next | `phase-0-foundation` | |
| 1 | Analysis engine v2 | [PHASE_1](docs/phases/PHASE_1_analysis_engine.md) | ⬜ | `phase-1-analysis-engine` | |
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

_(empty — Phase 0 not started)_

## Decisions log

| Date | Phase | Decision | Reason |
|---|---|---|---|
| 2026-10-01 | plan | Backend: FastAPI + SQLAlchemy 2 + Alembic. SQLite dev, Postgres prod. | Already on FastAPI. The same code works on both DBs. |
| 2026-10-01 | plan | Job queue = DB table + polling worker (no Redis/Celery) | Simple Windows dev. Low-volume, slow CV jobs. |
| 2026-10-01 | plan | Frontend = React + Vite + TS. Streamlit is retired in Phase 7. | A multi-page app with a reviewer workflow, auth, and an evidence player is beyond Streamlit. |
| 2026-10-01 | plan | Scoring rules live in versioned YAML rubrics. Results use versioned schema 2.0. | Thresholds change often. Historical results must stay explainable. |
| 2026-10-01 | plan | Review-first hard caps: no barcode or poor quality → never `pass` | The product principle in the README. |
| 2026-10-01 | plan | Rubric content inferred from `app.py` text | No official SOP doc yet (Open Question 1). |

## Open questions for the user (from IMPLEMENTATION.md §11)

1. Is there an official SOP document? — _unanswered_
2. Real sample videos plus a human-labeled eval set for Phase 6? — _unanswered_
3. GPU in production? — _unanswered_
4. Deploy target, storage (S3?), retention period? — _unanswered_
5. Integrations and webhooks? Keep the legacy `/analyze` endpoint? — _unanswered_

## Known issues / tech debt

- (baseline) `process_type` doesn't affect scoring. YOLO is loaded but unused. Models load at import. OCR cadence bug. Free +5 points. `estimated_sides` is hard-coded. → Phases 0–1.
- (baseline) The Streamlit app doesn't persist results. The API is synchronous and reads uploads into memory. → Phases 2 and 4.

## Session log

### 2026-10-01 — Planning session
- Analyzed the codebase (see IMPLEMENTATION.md §2). Recorded the test baseline.
- Created CLAUDE.md, IMPLEMENTATION.md, PROGRESS.md, PROMPTS.md, and docs/phases/PHASE_0..7.
- No code changes.

## Handoff notes for next session

**Start Phase 0.** Key pointers:
- The old analyzer with the motion/rotation and 6-side logic is at `git show 4973c0d~1:vms_sop_analyzer.py` (lines ~256–380). Port the *metrics* in Phase 0 and the *scoring* in Phase 1.
- `easyocr.Reader` is created at import in `vms_sop_analyzer.py`. That's why the tests take 18 s. Making it lazy is the first win.
- `app.py` lines ~178–187 have odd indentation inside `try:`. It's valid Python, but clean it up.
- Don't delete `audit_results.db`.
