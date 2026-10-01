# Phase 0 — Foundation & Cleanup

**Goal:** Turn the loose scripts into an installable, tested Python package with lazy model loading, config, and a green test suite. No new features. Behaviour stays the same except for the bug fixes listed below.

**Read:** IMPLEMENTATION.md §2 (current state), §3 (stack), §4 (layout).
**Branch:** `phase-0-foundation`

## Tasks

- [ ] **Repo hygiene:** extend `.gitignore` with `*.pt`, `*.db`, `data/`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `node_modules/`, `dist/`, and `training_images/`. Keep the untracked `yolov8n.pt` and `audit_results.db` on disk but ignored.
- [ ] Create `backend/pyproject.toml` (setuptools, package `vms`, `requires-python >=3.11`).
  - Core deps: fastapi, uvicorn[standard], python-multipart, pydantic>=2, pydantic-settings, opencv-contrib-python-headless, numpy, pyzbar, pyyaml.
  - `[ml]` extra: easyocr, ultralytics.
  - `[dev]` extra: pytest, pytest-cov, httpx, ruff, qrcode[pil].
  - Configure ruff and pytest in the same file (testpaths, `markers = models: needs EasyOCR/YOLO`, `addopts = -m "not models"`).
- [ ] `vms/config.py`: `Settings` (pydantic-settings, `env_prefix="VMS_"`, `.env`) with `data_dir`, `db_url`, `yolo_weights` (default `yolov8n.pt`), `ocr_enabled`, `yolo_enabled`, `process_fps=3`, `blur_threshold=30`, `max_upload_mb=500`. Add a `get_settings()` function cached with `lru_cache`.
- [ ] `vms/logging.py`: configure logging once (replaces `logging.basicConfig` at import time).
- [ ] Move the analyzer to `vms/analysis/legacy_analyzer.py` (class `VMSSOPAnalyzer`, same public API) and put the detectors behind **lazy singletons** in `vms/analysis/detectors/` (`get_ocr_reader()` and `get_yolo()` return `None` when the library is missing or disabled). Importing `vms` must not load torch.
- [ ] Bug fixes (these are fixes, not redesign):
  - OCR cadence uses the *sample* index (`i % 3`), not the raw frame index.
  - Remove the free `+5` "placeholder" points from step 4. Step 4 scoring stays at most 25 by giving product visibility 25 points. Update the UI weight only if it changed.
  - Compute `pct_*` metrics over **quality-valid frames** (and guard against division by zero).
  - Restore `metrics.direction_changes` and `metrics.estimated_sides` (0 for an empty video) using the motion/rotation logic from `git show 4973c0d~1:vms_sop_analyzer.py`. The *scoring* use of sides moves to Phase 1. For now only compute the metrics.
- [ ] Move `server.py` → `vms/api/main.py` (same endpoints for now: `/health`, `/analyze`, `/results`) and `audit_store.py` → `vms/legacy_store.py` (DB path from settings).
- [ ] Move `extract_frames.py` → `ml/extract_frames.py`.
- [ ] Keep `app.py` (Streamlit) at the root and switch its import to `from vms.analysis.legacy_analyzer import VMSSOPAnalyzer`. Fix the misindented `result = VMSSOPAnalyzer(` block. Remove `requirements.txt` or make it `-e backend[ml]` + streamlit + pandas so Streamlit Cloud still works. Update `package.json` scripts to the new entry points.
- [ ] Tests → `backend/tests/`:
  - `fixtures/video_factory.py`: `make_video(path, *, seconds, fps, size, qr_text=None, text=None, moving_box=False, blur=False, dark=False)`.
  - Port the 4 existing tests to pytest and make them pass.
  - Add tests: importing `vms` does not import `easyocr`/`ultralytics` (check `sys.modules`); settings env override works; the API `/health` and `/analyze` happy path works through `httpx`/`TestClient` with OCR disabled; a corrupt file returns 400.
  - Wrap the slow real-model test in `@pytest.mark.models`.
- [ ] `ruff check` and `ruff format` are clean.
- [ ] Rewrite `README.md` quickstart for the new layout (point to CLAUDE.md for dev workflow).

## Acceptance criteria

1. `pip install -e "backend[dev]"` works in a fresh venv **without** easyocr or ultralytics, and `pytest backend/tests -q` passes in under 30 s.
2. `pip install -e "backend[dev,ml]"`, then `pytest backend/tests -q -m models` passes.
3. `uvicorn vms.api.main:app` serves `/health` and `/analyze` and returns the same v1 result shape as before, plus the restored `direction_changes` metric.
4. `streamlit run app.py` still works.
5. An empty video scores 0. No models load at import.
6. `git status` shows no `.pt` or `.db` files as untracked.

## Out of scope

Rubric YAML, the new result schema, the DB redesign, auth, and the frontend.

## Handoff notes to write in PROGRESS.md

The final package layout, how to run tests, any dependency pinning problems on Python 3.13 (torch/easyocr), and how long the slow model tests take.
