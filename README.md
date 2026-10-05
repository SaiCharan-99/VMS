# VMS SOP Analyzer

Warehouse operators record a video of every parcel they pack (Forward) or unbox (Return). This
app scores each video against the VMS SOP checklist with computer vision (barcode decoding, OCR,
object detection, motion) and returns **pass / review / fail**. It is **review-first**: weak or
unclear evidence becomes `review`, never `pass`, and human reviewers settle those cases with a
full audit trail.

```
Browser ──▶ web (nginx: React UI, /api proxy) ──▶ api (FastAPI) ──▶ Postgres
                                                       ▲                ▲
                         data volume (videos, evidence frames)    worker × N (analysis jobs)
```

No external accounts or API keys are needed. Every model (EasyOCR, YOLOv8n) is open source and
baked into the Docker image, so analysis runs offline.

---

## Quick setup (one command)

**Requirement:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and
running. Nothing else (no Python or Node needed).

1. Clone and enter the repo:
   ```bash
   git clone https://github.com/SaiCharan-99/VMS.git
   cd VMS
   ```
2. Run the setup script for your OS:
   - **Windows (PowerShell):**
     ```powershell
     powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
     ```
   - **macOS / Linux:**
     ```bash
     bash scripts/setup.sh
     ```
3. Open the URL the script prints (normally **http://localhost**) and sign in with a demo login:

   | Role | Email | Password |
   |---|---|---|
   | Admin | `admin@vms.local` | `admin-demo-1` |
   | Reviewer | `reviewer@vms.local` | `reviewer-demo-1` |
   | Operator | `operator@vms.local` | `operator-demo-1` |

That's all. The first run builds the images (5–15 minutes, it downloads the ML libraries);
later runs take seconds.

What the script does, in order:
1. Checks that Docker is installed and running.
2. Creates `.env` from `.env.example` with a random JWT secret and Postgres password, and picks
   free host ports (web 80 → 8080 → …; skips ports already in use). An existing `.env` is kept.
3. Runs `docker compose up -d --build --wait` (Postgres, migrations, API, worker, web).
4. Creates the demo logins (`python -m vms.cli seed-demo`).

Options: `-NoDemo` / `--no-demo` (skip demo users), `-NoML` / `--no-ml` (small image without
OCR/YOLO; builds in ~1 minute but scores weaker).

### Instructions for AI coding agents

If you are an AI agent asked to set this project up, do exactly this and do not ask the user to
run commands:

1. Confirm Docker is available: `docker info` must succeed. If it fails, start Docker Desktop
   (Windows: `"C:\Program Files\Docker\Docker\Docker Desktop.exe"`) and wait until `docker info`
   succeeds.
2. From the repo root, run `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` on Windows
   or `bash scripts/setup.sh` elsewhere. It is idempotent; re-run it if interrupted.
3. Verify: `curl http://localhost:<port>/api/v1/health` returns `"status":"ok"` (the port is
   `VMS_HTTP_PORT` in `.env`).
4. Report the URL and the demo logins above to the user.
5. Never commit `.env`, `data/`, videos or `*.pt` files. Never delete `data/` or the Docker volumes
   (`docker compose down -v`) without asking: they hold audit records.

Developers and agents changing the code: read [CLAUDE.md](CLAUDE.md) (conventions, commands,
session protocol) and [PROGRESS.md](PROGRESS.md) (current state) first.

---

## Using the app

1. **Upload** (any role): drop one or more videos, choose Forward or Return, optionally an AWB and
   station. Each video is queued and analyzed by a worker; the verdict appears in the list.
2. **Inspections**: search and filter videos; open one to see the player, an evidence timeline,
   the score per SOP step and every check.
3. **Review queue** (reviewer/admin): settle `review` cases with the keyboard (P = pass,
   F = fail, 1–7 = reason, N = next). The human decision becomes the final status.
4. **Reports** (reviewer/admin): pass rate, review rate, model–human agreement, most-missed checks,
   CSV export.
5. **Admin**: users, warehouses and stations, API keys for integrations, audit log.

Reviewers can **mark a video disputed** on its detail page; retention never deletes a disputed
video's file.

## Everyday commands

| Task | Command |
|---|---|
| Stop | `docker compose down` |
| Start again | `docker compose up -d` |
| Live logs | `docker compose logs -f api worker` |
| More analysis throughput | `docker compose up -d --scale worker=3` |
| Create a real admin | `docker compose exec api python -m vms.cli create-admin --email you@company.com --name "Your Name"` |
| Delete old video files (rows + evidence kept) | `docker compose exec api python -m vms.cli purge --older-than-days 180` |
| Update after `git pull` | `docker compose up -d --build --wait` (migrations run automatically) |

Production deployment (real secrets, backups, upgrades, GPU notes): [docs/DEPLOY.md](docs/DEPLOY.md).
API usage with API keys: [docs/API.md](docs/API.md). Operator guide to the SOP checks:
[docs/SOP.md](docs/SOP.md).

## Do I need to train a model?

No. Out of the box it uses barcode decoding, a pretrained OCR model, a general pretrained object
detector and image heuristics, scored by the `forward-v1` / `return-v1` rubrics. Expect a fairly
high `review` rate on real footage until thresholds are calibrated on your own labelled videos
(`ml/evaluate.py`, `ml/calibrate.py`) and, later, a custom detector is trained (`ml/train.py`,
see `ml/dataset/README.md`).

## Project layout

```
backend/vms/          Python package: analysis pipeline, YAML rubrics, API, worker, CLI
backend/alembic/      database migrations
backend/tests/        pytest suite (synthetic videos, SQLite and Postgres)
frontend/             React + Vite + TypeScript UI, nginx config, Playwright smoke test
ml/                   evaluation, calibration, frame extraction, YOLO training
scripts/              one-command setup
docs/                 deploy, API, SOP guide, UI design, phase plans
docker-compose.yml    production stack; docker-compose.override.yml adds dev conveniences
```

## Development without Docker (optional)

Needs Python 3.11+ and Node 22. In PowerShell from the repo root:

```powershell
py -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e "backend[dev,ml]"
alembic -c backend/alembic.ini upgrade head
python -m vms.cli seed-demo
uvicorn vms.api.main:app --reload --port 8000      # terminal 1
python -m vms.worker                                # terminal 2
cd frontend; npm install; npm run dev               # terminal 3 -> http://localhost:5173
```

Checks: `pytest backend/tests -q`, `ruff check backend`, and in `frontend/`:
`npm run typecheck`, `npm run lint`, `npm test`, `npm run build`. CI runs all of these plus a
Postgres test leg and a Playwright smoke test against the Docker stack.
