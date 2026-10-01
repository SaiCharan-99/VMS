# PROMPTS.md — Session Kickoff Prompts

Each phase runs in a **new Claude Code session**. Paste the matching prompt as the first message. The prompts are self-contained, and the repo docs carry the rest of the context.

---

## Generic: start the next phase

```
Read CLAUDE.md and PROGRESS.md, then start the current phase listed in PROGRESS.md.
Follow the session protocol in CLAUDE.md exactly: read the phase spec in docs/phases/,
run the test baseline, create the phase branch, copy the task checklist into PROGRESS.md,
implement every task, verify every acceptance criterion, and finish by updating PROGRESS.md
(status, ticked tasks, decisions, known issues, session log, handoff notes) and committing.
Ask me only if you're blocked on something that's genuinely my decision.
```

## Generic: resume an unfinished phase

```
Read CLAUDE.md and PROGRESS.md. The current phase is partially done. Check the ticked
checklist and the session log, check `git status` / `git log` on the phase branch,
run the tests, then continue with the remaining tasks. Update PROGRESS.md before you finish.
```

## Generic: wrap up (when the context is getting long or you need to stop)

```
Stop implementing. Make sure the code compiles and tests pass (or record what's failing).
Commit work in progress on the phase branch, then update PROGRESS.md: tick completed
tasks, add a session log entry, record decisions and known issues, and write precise
handoff notes (what's done, what's next, any half-finished work and where it lives) so
a fresh session can continue.
```

---

## Phase 0 — Foundation & cleanup

```
Read CLAUDE.md and PROGRESS.md, then do Phase 0 per docs/phases/PHASE_0_foundation.md.
Goal: restructure the loose scripts into the backend/vms package with pyproject extras,
settings, lazy model loading, the listed bug fixes, and a fast green pytest suite, while
keeping /analyze and the Streamlit app working. Follow the CLAUDE.md session protocol and
update PROGRESS.md with handoff notes for Phase 1 when done.
```

## Phase 1 — Analysis engine v2

```
Read CLAUDE.md and PROGRESS.md, then do Phase 1 per docs/phases/PHASE_1_analysis_engine.md.
Build the modular pipeline (sampling → detectors → metrics → YAML rubric → decision +
caps → evidence) producing the schema 2.0 AnalysisResult from IMPLEMENTATION.md §5–6,
with separate forward-v1/return-v1 rubrics and a CLI. Keep the v1 wrapper so app.py and
/analyze still work. Record measured timings and metric keys in PROGRESS.md.
```

## Phase 2 — Data layer, jobs, API v1

```
Read CLAUDE.md and PROGRESS.md, then do Phase 2 per docs/phases/PHASE_2_data_jobs_api.md.
Add SQLAlchemy models for the whole data model in IMPLEMENTATION.md §7 with Alembic,
local storage, the DB-backed job queue and `python -m vms.worker`, the /api/v1 video,
job, and evidence endpoints (auth stubbed), the legacy compatibility routes, and the legacy
DB import. Verify upload → async analysis → result end to end, then update PROGRESS.md.
```

## Phase 3 — Auth, roles, audit

```
Read CLAUDE.md and PROGRESS.md, then do Phase 3 per docs/phases/PHASE_3_auth_users.md.
Add JWT login, argon2 passwords, API keys, operator/reviewer/admin role guards on every
route (with a parametrized role-matrix test), operator data isolation, admin CRUD for
users/warehouses/stations/keys, audit logging, and the create-admin / seed-demo CLI.
Update PROGRESS.md with demo credentials and handoff notes.
```

## Phase 4 — Web frontend (core)

```
Read CLAUDE.md and PROGRESS.md, then do Phase 4 per docs/phases/PHASE_4_frontend.md.
Scaffold frontend/ (React + Vite + TS + Tailwind + TanStack Query) and build login,
upload with live job progress, the videos list with filters, and the video detail page with
player, evidence timeline, and step cards, keeping the dark visual style of app.py.
Make build, lint, typecheck, and tests clean, run the app, and confirm the full flow in the
browser. Then update PROGRESS.md.
```

## Phase 5 — Review workflow, reports, admin

```
Read CLAUDE.md and PROGRESS.md, then do Phase 5 per docs/phases/PHASE_5_review_reports_admin.md.
Build the reviewer queue with keyboard shortcuts and reason codes, report endpoints and the
/reports page with charts and CSV export, the admin screens (users, stations, API keys,
audit log), and docs/SOP.md. Verify the report math with a backend test. Then update
PROGRESS.md.
```

## Phase 6 — ML training & evaluation

```
Read CLAUDE.md and PROGRESS.md, then do Phase 6 per docs/phases/PHASE_6_ml_training_eval.md.
Build the evaluation harness first (false-pass rate is the key metric), then the frame
extraction, annotation guide, YOLO training script, model-card-driven class mapping, the v2
rubrics, and the calibration tool. Real videos are in data/samples/ and labels are in
data/eval/labels.csv (if they're missing, build and test everything on synthetic data and
record the blocker). Record v1 vs v2 eval numbers in PROGRESS.md.
```

## Phase 7 — Production hardening & deploy

```
Read CLAUDE.md and PROGRESS.md, then do Phase 7 per docs/phases/PHASE_7_production.md.
Add Docker/Compose with Postgres and scalable workers, observability, retention, CI with
a Postgres matrix and a Playwright smoke test, a security review, OpenAPI type sync, legacy
removal (ask me about keeping /analyze if PROGRESS.md doesn't record an answer), and
DEPLOY/API docs. Mark v1.0 in PROGRESS.md when all acceptance criteria pass.
```

---

## Useful one-off prompts

**Answer the open questions** (run anytime, then continue the current phase):
```
Here are answers to the open questions in PROGRESS.md: <answers>. Record them in the
Decisions log and update IMPLEMENTATION.md and any affected phase specs accordingly.
```

**Review a finished phase before merging:**
```
Read CLAUDE.md and PROGRESS.md. Review branch phase-<N>-<slug> against
docs/phases/PHASE_<N>_*.md: check every acceptance criterion by actually running it, run
/code-review, and list gaps. Fix what's in scope and record the rest in PROGRESS.md.
```

**Change the SOP rubric:**
```
The SOP changed: <describe>. Create a new rubric version (do not edit the existing YAML),
update tests, make it the active rubric via settings, and log the decision in PROGRESS.md.
```
