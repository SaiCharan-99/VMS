# CLAUDE.md — VMS SOP Analyzer

Read this first in **every** session. This project is built in phases, and each phase runs in a **new session** with no memory of earlier ones. These files carry the context between sessions:

| File | Purpose | When to read |
|---|---|---|
| `CLAUDE.md` (this file) | What we're building, conventions, commands, session protocol | Always, first |
| `PROGRESS.md` | Which phase is current, what's done, decisions, handoff notes | Always, second |
| `IMPLEMENTATION.md` | Architecture, data model, API contract, analysis-result schema, rubric spec | The sections your phase links to |
| `docs/phases/PHASE_N_*.md` | Task list, file plan, and acceptance criteria for one phase | Only the current phase |
| `docs/UI_DESIGN.md` + `docs/ui/mockup.html` | UI design system and clickable visual target | Any frontend work (Phases 4–5) |
| `PROMPTS.md` | Prompts the user pastes to start sessions | Not needed by Claude |

## What the product is

**VMS** is a logistics company. Warehouse operators record a video of every parcel they handle, and that video is the evidence used to settle disputes (for example "item missing", "wrong item", "damaged", or "tag removed" claims).

- **Forward (packing):** show the shipping label and barcode, show the product unfolded and inspected, show brand tags and hangtags, then pack and seal on camera.
- **Return (unboxing):** show the outer AWB label and barcode, show the seal and all 6 sides before opening, open on camera, show brand tags and hangtags, and show the product unfolded on both sides and checked for damage or fraud.

The **VMS SOP Analyzer** scores each video against the SOP rubric (4 steps, 100 points) using computer vision: frame quality, barcode decoding, OCR, object detection, and motion/rotation. It returns **pass / review / fail**. The system is **review-first**: when it is uncertain, it must say `review`. It must never auto-approve on weak evidence. Human reviewers settle the `review` cases, and every decision is kept as an audit trail.

## Target architecture (summary; full detail in IMPLEMENTATION.md)

```
frontend/ (React+Vite+TS)  ──HTTP──▶  backend/vms/api (FastAPI, /api/v1)
                                          │  writes jobs
                                          ▼
                                   SQLite (dev) / Postgres (prod)  ◀── backend/vms/worker (polls jobs, runs analysis)
                                          │
                                   data/ (videos, evidence frames)    backend/vms/analysis (CV pipeline + YAML rubrics)
ml/ (frame extraction, YOLO training, evaluation harness)
```

## Conventions

- **Python 3.11+** (the dev machine has 3.13). Backend code lives under `backend/vms/` as one package. Use type hints everywhere, Pydantic v2 for schemas, and SQLAlchemy 2.0 style (`Mapped[...]`, `select()`).
- **Heavy ML models (EasyOCR, YOLO) load lazily** through `vms.analysis.detectors` singletons. Never load them at import time. Tests must be able to run without them (detectors report `available=False`, and the pipeline degrades gracefully).
- **Scoring rules live in YAML rubrics** (`backend/vms/analysis/rubrics/*.yaml`), not in Python `if` chains. The pipeline computes *metrics*, and the rubric turns metrics into points.
- **The analysis result is a versioned contract** (`schema_version`; see IMPLEMENTATION.md §5). Do not change its shape without bumping the version and updating the frontend types.
- **Config comes from env vars** through `vms.config.Settings` (pydantic-settings, `VMS_` prefix, `.env` supported). Do not hard-code paths, secrets, or thresholds.
- **API:** every route is under `/api/v1`, errors return `{"detail": ...}`, list endpoints are paginated (`page`, `page_size` → `{items, total, page, page_size}`).
- **Tests:** pytest under `backend/tests/`. Generate synthetic videos with `tests/fixtures/video_factory.py`. Never commit real videos (they're gitignored, and real sample videos go in `data/samples/`). Mark tests that need real models with `@pytest.mark.models`; they're skipped by default.
- **UI:** follow `docs/UI_DESIGN.md`. Use only the design tokens and `src/components/ui` primitives. Green, amber, and red are reserved for pass, review, and fail.
- **Lint and format:** `ruff check` and `ruff format`. Frontend: ESLint plus Prettier defaults, and strict TypeScript.
- **Code style:** small modules, no dead code, and comments only where the *why* isn't obvious.
- **Windows-first dev:** commands must work in PowerShell. Use `pathlib`, not string paths.

## Commands

These are valid from Phase 0 onward. If a command doesn't work yet, check PROGRESS.md for the current state.

```powershell
# backend setup
py -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e "backend[dev]"            # add ,ml for easyocr+ultralytics
# tests / lint
pytest backend/tests -q                  # fast suite (no heavy models)
pytest backend/tests -q -m models        # suite needing EasyOCR/YOLO
ruff check backend; ruff format backend
# run
alembic -c backend/alembic.ini upgrade head     # from Phase 2
uvicorn vms.api.main:app --reload --port 8000    # API → http://localhost:8000/docs
python -m vms.worker                             # job worker (from Phase 2)
python -m vms.cli seed-demo                      # dev logins (see PROGRESS.md handoff)
cd frontend; npm install; npm run dev            # UI → http://localhost:5173 (from Phase 4)
cd frontend; npm run build; npm run lint; npm test; npm run typecheck   # frontend checks
```

## Session protocol (follow every session)

1. Read `CLAUDE.md`, then `PROGRESS.md`. Find the **current phase** and read its **handoff notes**.
2. Read `docs/phases/PHASE_<N>_*.md` and the IMPLEMENTATION.md sections it references.
3. Run the test suite before changing anything. If the baseline is red, record it in PROGRESS.md and fix it first (unless it's out of scope, in which case note it).
4. Work on branch `phase-<N>-<slug>`, created from `main`. Commit in logical steps.
5. Work through the phase task list. When reality differs from the plan, make a sensible call, then record it under **Decisions** in PROGRESS.md (and update IMPLEMENTATION.md if a contract changed).
6. Before finishing, check every **acceptance criterion** in the phase doc and run tests and lint.
7. Update `PROGRESS.md`: phase status, a ticked task list, a session log entry, decisions, known issues, and **handoff notes for the next phase**. This is mandatory. The next session only knows what you write down.
8. Do not start the next phase in the same session unless the user asks you to.

## Scope guards

- Do not delete `audit_results.db` or anything in `data/`. They may contain real audit records.
- Do not commit model weights (`*.pt`), videos, `.env`, or `data/`.
- Do not weaken the review-first rule. A missing barcode or poor video quality must never produce `pass`.
