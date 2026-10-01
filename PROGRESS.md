# PROGRESS.md — Project State & Handoff Log

> **Every session:** read this after CLAUDE.md. **Before ending a session:** update the status table, tick tasks, add a session log entry, record decisions and known issues, and write handoff notes. The next session has no other memory.

## Current phase: **Phase 2 — Data layer, jobs, API v1** (not started; Phase 1 done)

## Phase status

| # | Phase | Spec | Status | Branch | Completed |
|---|---|---|---|---|---|
| — | Codebase analysis & planning | this file, IMPLEMENTATION.md | ✅ done | `main` | 2026-10-01 |
| 0 | Foundation & cleanup | [PHASE_0](docs/phases/PHASE_0_foundation.md) | ✅ done | `phase-0-foundation` | 2026-10-01 |
| 1 | Analysis engine v2 | [PHASE_1](docs/phases/PHASE_1_analysis_engine.md) | ✅ done | `phase-1-analysis-engine` | 2026-10-01 |
| 2 | Data layer, jobs, API v1 | [PHASE_2](docs/phases/PHASE_2_data_jobs_api.md) | ⏳ next | `phase-2-data-jobs-api` | |
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

## Open questions for the user (from IMPLEMENTATION.md §11)

1. Is there an official SOP document? — _unanswered_
2. Real sample videos plus a human-labeled eval set for Phase 6? — _unanswered_
3. GPU in production? — _unanswered_
4. Deploy target, storage (S3?), retention period? — _unanswered_
5. Integrations and webhooks? Keep the legacy `/analyze` endpoint? — _unanswered_

## Known issues / tech debt

- Fixed in Phase 1: `process_type` now selects the rubric; YOLO is used; `estimated_sides` is scored (Return `six_sides`).
- Heuristic weaknesses for Phase 6: (a) the label / tag / package contour heuristics fire on almost any textured frame (label_ratio ≈ 1.0 on synthetic video), so they barely discriminate. (b) Motion magnitude is the **mean over the whole frame**, so small moving objects stay below `ACTIVE_MAGNITUDE` (a 60 s synthetic box gives 0 direction changes), and the left-vs-right-half direction heuristic can flip as one object crosses the centre (a monotonic 3 s move gives 2 changes). (c) The `avg_text_blocks` thresholds (>5 / >3) came from v1 `readtext` counts and haven't been re-tuned on real footage for `detect()` at 480 px. (d) The COCO class map is a stopgap.
- No real sample videos yet (`data/samples/` is empty). The timings below come from a synthetic video.
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

### 2026-10-01 — Phase 1 session
- Baseline 16 passed. Branch `phase-1-analysis-engine` (from `phase-0-foundation`).
- Built the v2 pipeline, rubrics, CLI, and tests. Fast suite: **57 passed in ~8 s**. `-m models`: 1 passed (~16 s). `ruff check` / `ruff format` clean.
- **Measured (16-thread Windows laptop, CPU only, OCR + YOLO on):** a synthetic 60 s 1280×720 30 fps video (QR + text + moving box) gives 180 sampled frames. Analysis **45.3 s**; CLI wall clock **46.8 s** including model load. Breakdown (ms): sampling 942, quality 543, motion 2128, objects (heuristics + yolov8n) 8041, barcode 1316, OCR 26996 (≈60 calls × 0.45 s), scoring 1, evidence 8. Before switching OCR to 480 px detect-only with onset triggering: 142 s.
- Acceptance: (1) the CLI writes a schema-valid result and 4 evidence JPEGs ✔. (2) `test_yaml_threshold_change_changes_score` ✔. (3) `test_shipped_caps_block_pass` plus the pipeline dark/blur tests ✔. (4) suite 8 s; 60 s video 45 s ✔. (5) `/analyze` is covered by `test_api.py` (v1 shape). `app.py` was verified headless with Streamlit AppTest and a stubbed upload in both modes (no exceptions; titles and CSV columns come from the rubric) ✔.

## Handoff notes for next session

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
