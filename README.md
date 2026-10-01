# VMS SOP Analyzer

Scores warehouse inspection videos (forward packing / return unboxing) against the VMS SOP
rubric using computer vision, and returns **pass / review / fail**. The system is review-first:
uncertain evidence becomes `review`, never `pass`.

Developer workflow, conventions and phase plan: see [CLAUDE.md](CLAUDE.md) and
[PROGRESS.md](PROGRESS.md).

## Layout

```
backend/vms/            Python package (config, analysis, API, legacy store)
backend/tests/          pytest suite (synthetic videos via tests/fixtures/video_factory.py)
ml/                     training utilities (frame extraction)
app.py                  Streamlit demo UI (retired in Phase 7)
```

## Quickstart (PowerShell)

```powershell
py -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e "backend[dev,ml]"          # drop ",ml" to skip EasyOCR/YOLO (tests still pass)
pytest backend/tests -q                   # fast suite
uvicorn vms.api.main:app --reload --port 8000   # http://localhost:8000/docs
pip install streamlit pandas; streamlit run app.py
```

Settings come from `VMS_*` environment variables or a `.env` file (see `backend/vms/config.py`),
e.g. `VMS_OCR_ENABLED=false`, `VMS_PROCESS_FPS=3`, `VMS_DB_URL=sqlite:///audit_results.db`.

## Example upload

```bash
curl -X POST "http://localhost:8000/analyze" -F "file=@sample_video.mp4" -F "process_type=Return"
```
