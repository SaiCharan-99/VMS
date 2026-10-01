# VMS SOP Analyzer

Scores warehouse inspection videos (forward packing / return unboxing) against the VMS SOP
rubric using computer vision, and returns **pass / review / fail**. The system is review-first:
uncertain evidence becomes `review`, never `pass`.

Developer workflow, conventions and phase plan: see [CLAUDE.md](CLAUDE.md) and
[PROGRESS.md](PROGRESS.md).

## Layout

```
backend/vms/            Python package (config, analysis, db, services, storage, worker, API)
backend/alembic/        DB migrations
backend/tests/          pytest suite (synthetic videos via tests/fixtures/video_factory.py)
frontend/               React + Vite + TS web app (VMS Inspect)
ml/                     training utilities (frame extraction)
app.py                  Streamlit demo UI: DEPRECATED, replaced by frontend/, deleted in Phase 7
```

## Quickstart (PowerShell)

```powershell
py -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e "backend[dev,ml]"          # drop ",ml" to skip EasyOCR/YOLO (tests still pass)
pytest backend/tests -q                   # fast suite
alembic -c backend/alembic.ini upgrade head     # creates data/vms.db
uvicorn vms.api.main:app --reload --port 8000   # http://localhost:8000/docs
python -m vms.worker                      # second terminal: runs queued analyses
python -m vms.cli seed-demo               # dev only: demo warehouse + operator/reviewer/admin logins
cd frontend; npm install; npm run dev     # third terminal: http://localhost:5173 (proxies /api to :8000)
python -m vms.cli import-legacy --db audit_results.db   # once: old results -> new DB
```

The old Streamlit UI (`streamlit run app.py`) is deprecated; use the web app instead.
Frontend checks: `npm run build`, `npm run lint`, `npm test`, `npm run typecheck` (in `frontend/`).

Settings come from `VMS_*` environment variables or a `.env` file (see `backend/vms/config.py`),
e.g. `VMS_OCR_ENABLED=false`, `VMS_PROCESS_FPS=3`, `VMS_DB_URL=sqlite:///data/vms.db`. See `.env.example`.

## Example upload

```bash
curl -F "file=@sample_video.mp4" -F "process_type=Return" http://localhost:8000/api/v1/videos   # 201 {video, job}
curl http://localhost:8000/api/v1/jobs/1        # poll until status is done
curl http://localhost:8000/api/v1/videos/1      # video + full result + evidence URLs
```

The legacy synchronous `POST /analyze` and `GET /results` still work (v1 shape).
