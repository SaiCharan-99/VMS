# IMPLEMENTATION.md — Architecture & Contracts

This is the shared reference for all phases. Phase docs in `docs/phases/` point to sections here. If you change a contract (schema, API, data model), update this file in the same commit.

---

## 1. Problem statement

VMS warehouse operators film every **Forward** (packing) and **Return** (unboxing) operation. These videos are the evidence used in customer and marketplace disputes. A video is only useful if the operator followed the SOP on camera. Checking videos by hand doesn't scale, so the system must:

1. Ingest videos (single or batch, from a browser or from other systems through the API).
2. Score each video automatically against the SOP rubric for its process type.
3. Route uncertain results to human reviewers. Reviewers can override decisions, and their reason is kept.
4. Keep a searchable audit trail: find a video by AWB or barcode, see why it passed or failed, and jump to the evidence frame.
5. Report compliance over time, by warehouse, station, and operator, and show the most common SOP failures.
6. Improve accuracy over time by training custom detectors on the company's own footage.

### SOP rubric (current understanding — confirm with VMS ops, see Open Questions)

| # | Step | Points | Forward (packing) | Return (unboxing) |
|---|---|---|---|---|
| 1 | Shipping label & barcode | 30 | Label visible and barcode readable before sealing | Outer AWB label held toward the camera before opening |
| 2 | Packing & sealing / Seal & unboxing | 20 | Item packed correctly, bag or box fully sealed on camera | Seal inspected for tampering, all 6 sides shown, opened on camera |
| 3 | Brand tag & hangtag | 25 | Tags attached and visible before packing | Brand labels and price tags shown close to the camera |
| 4 | Product condition | 25 | Item unfolded and inspected before packing | Item fully unfolded, both sides shown, checked for damage |

Decision: **pass** if score ≥ 85 and confidence ≥ 0.70. **review** if score ≥ 50 and confidence ≥ 0.40. Otherwise **fail**. The hard caps in §6 apply on top of this.

---

## 2. Current state (analysis of the code as of 2026-10-01, commit `4973c0d`)

| File | What it does | Problems |
|---|---|---|
| `vms_sop_analyzer.py` | Samples about 3 fps and resizes frames to 640px wide. Per frame it checks blur and brightness, counts EasyOCR text blocks, finds contours as a heuristic for labels, packages, and tags, and decodes barcodes with pyzbar. Scores 4 steps and returns pass/review/fail. | **`process_type` is ignored**: the latest rewrite dropped the Forward/Return logic and the 6-side rotation estimate (both existed in `4973c0d~1`). **YOLO is loaded but never used.** EasyOCR and YOLO load **at import time**, which slows every import and test. `idx % 3` runs on the raw frame index, not the sample index, so OCR cadence is erratic. Step 4 gives **+5 free points**, so an empty video scores 5. `pct_*` metrics divide by all frames, including rejected ones. `min_hold_sec` is unused. "Product" detection reuses package detection. `estimated_sides` is hard-coded to 1. No evidence frames or timestamps are kept. |
| `app.py` | Streamlit batch UI: per-video score cards, step bars, and CSV export. | Does not save results to the store. Duplicates the rubric (weights and descriptions) in UI code. Synchronous. No auth. |
| `server.py` | FastAPI: `GET /health`, `POST /analyze` (synchronous), `GET /results`. Saves to SQLite. | Reads the whole upload into memory. No size limit. Analysis blocks the request. Does not keep the video, so you can't re-review or re-analyze it. No auth. |
| `audit_store.py` | SQLite `results` table holding a JSON blob. | Single flat table. No reviews, users, evidence, or migrations. |
| `extract_frames.py` | Dumps every Nth frame for annotation. | Fine. It will move into `ml/`. |
| `test_vms_sop_analyzer.py` | 4 unittest tests. | **1 failing** (`empty video → score 0`, plus it expects a `direction_changes` metric). Tests load the real EasyOCR, so they're slow (about 18 s). |
| Misc | `package.json` holds npm script shortcuts only. `packages.txt` lists `libzbar0` (Streamlit Cloud). | `yolov8n.pt` and `audit_results.db` are untracked and need gitignore entries. |

What's worth keeping: the overall approach (sampling → quality gate → detectors → rubric → decision), the confidence formula idea, the review-first principle, the Streamlit UI's step-card UX (copy it into React), the QR-video test fixture technique, and the motion/rotation logic in the previous commit (`git show 4973c0d~1:vms_sop_analyzer.py`, lines ~256–380).

---

## 3. Target architecture

```
                ┌──────────────────────────┐
 Browser ──────▶│ frontend (React/Vite/TS) │
                └────────────┬─────────────┘
                             │ /api/v1 (JWT)
 3rd-party  ────────────────▶│
 systems (API key)           ▼
                ┌──────────────────────────┐      ┌────────────────────────┐
                │ vms.api (FastAPI)         │─────▶│ DB: SQLite dev /       │
                │  routers, auth, schemas   │      │     Postgres prod      │
                └────────────┬─────────────┘      └───────────▲────────────┘
                             │ save file + enqueue job          │ claim job / write results
                             ▼                                  │
                ┌──────────────────────────┐      ┌────────────┴───────────┐
                │ vms.storage (local FS →   │◀────│ vms.worker (N procs)    │
                │   S3-compatible later)    │      │  runs vms.analysis      │
                └──────────────────────────┘      └────────────────────────┘
```

**Stack decisions** (change only by recording the reason in PROGRESS.md → Decisions):

| Concern | Choice | Why |
|---|---|---|
| API | FastAPI + Pydantic v2 | Already in use. Async uploads and OpenAPI docs. |
| ORM / migrations | SQLAlchemy 2.0 + Alembic | The same code runs on SQLite (dev) and Postgres (prod). |
| Job queue | **DB-backed jobs table** plus a polling worker process | No Redis or Celery needed, which keeps Windows dev simple. CV jobs are slow and low-volume, so polling every 1–2 s is fine. |
| File storage | `vms.storage.Storage` interface, `LocalStorage` implementation under `data/` | You can swap in S3/MinIO later without touching callers. |
| Auth | JWT access tokens (PyJWT) + argon2 password hashes. API keys for machine clients. | Simple and stateless. |
| Frontend | React 18, Vite, TypeScript, Tailwind, TanStack Query, React Router, Recharts | A real multi-page app with a reviewer workflow, which Streamlit can't do well. |
| CV | OpenCV, pyzbar, EasyOCR (CPU), Ultralytics YOLOv8 | Already chosen. Custom YOLO weights come in Phase 6. |
| Packaging | `backend/pyproject.toml` with extras `[dev]` and `[ml]` | Lets tests and CI skip the heavy ML dependencies. |
| Deploy | Docker Compose: api, worker, frontend (nginx), postgres | Phase 7. |

---

## 4. Target repository layout

```
backend/
  pyproject.toml
  alembic.ini
  alembic/                     # migrations
  vms/
    __init__.py                # __version__
    config.py                  # Settings (pydantic-settings, VMS_ prefix)
    logging.py
    analysis/
      __init__.py              # analyze_video(path, process_type, settings) -> AnalysisResult
      pipeline.py              # orchestrates sampling → detectors → metrics → rubric
      sampling.py              # frame sampling, video metadata
      metrics.py               # aggregate per-frame signals → metric dict
      rubric.py                # load YAML rubric, evaluate checks, decision + caps
      confidence.py
      result.py                # Pydantic AnalysisResult (schema §5)
      evidence.py              # pick & save best frame per step
      detectors/
        base.py                # Detector protocol, availability flag
        quality.py  barcode.py  ocr.py  objects.py  motion.py  heuristics.py
      rubrics/
        forward-v1.yaml  return-v1.yaml
    db/
      base.py  session.py  models.py
    storage.py
    services/                  # business logic used by API & worker
      videos.py  jobs.py  reviews.py  reports.py  audit.py  users.py
    api/
      main.py  deps.py  errors.py
      schemas/                 # request/response models
      routers/  health.py auth.py videos.py jobs.py analyses.py reviews.py reports.py admin.py legacy.py
    worker.py                  # `python -m vms.worker`
    cli.py                     # `python -m vms.cli create-admin | import-legacy | analyze <file>`
  tests/
    conftest.py
    fixtures/video_factory.py
    analysis/  api/  services/
frontend/
  package.json  vite.config.ts  tailwind.config.ts  src/{api,components,pages,hooks,lib,types}
ml/
  extract_frames.py  dataset/README.md  data.yaml  train.py  evaluate.py  eval_labels.example.csv
docs/
  phases/PHASE_*.md
  SOP.md                       # rubric explained for ops users (Phase 5)
  DEPLOY.md                    # Phase 7
data/                          # gitignored: videos/, evidence/, samples/, eval/, models/
docker-compose.yml  .env.example
```

Migration path for the legacy root files: Phase 0 moves `vms_sop_analyzer.py`, `audit_store.py`, `server.py`, and `extract_frames.py` into the new layout. `app.py` (Streamlit) keeps working by importing `vms.analysis` until Phase 4 replaces it. Phase 7 deletes it.

---

## 5. Analysis result contract (`schema_version: "2.0"`)

The pipeline returns this as a Pydantic model (`vms.analysis.result.AnalysisResult`), stores it as JSON in `analyses.result_json`, and the frontend mirrors it in `src/types/analysis.ts`.

```jsonc
{
  "schema_version": "2.0",
  "process_type": "Return",                 // "Forward" | "Return"
  "rubric_id": "return-v1",
  "engine": {
    "version": "0.2.0",
    "detectors": { "ocr": true, "barcode": true, "objects": "yolov8n.pt", "motion": true }
  },
  "video": { "duration_s": 42.3, "fps": 30.0, "frames_total": 1269, "frames_sampled": 127, "width": 1280, "height": 720 },
  "quality": { "frames_ok": 119, "frames_blurry": 6, "frames_dark": 2, "avg_blur": 88.1, "avg_brightness": 121.4, "ok_ratio": 0.94 },
  "barcodes": [ { "value": "AWB123456789", "symbology": "CODE128", "first_seen_s": 3.2, "frames_seen": 9 } ],
  "metrics": {                               // flat dict of floats/ints/bools; rubric checks reference these keys
    "label_ratio": 0.31, "package_ratio": 0.72, "tag_ratio": 0.18, "product_ratio": 0.44,
    "avg_text_blocks": 6.2, "barcode_found": true, "duration_s": 42.3,
    "estimated_sides": 5, "direction_changes": 4, "motion_ratio": 0.38, "max_label_hold_s": 2.7,
    "barcode_count": 1, "end_activity_ratio": 0.6, "quality_ok_ratio": 0.94, "frames_sampled": 127
  },
  "steps": [
    {
      "key": "shipping_label", "title": "Shipping Label & Barcode", "weight": 30, "score": 30,
      "status": "met",                       // met (=weight) | partial (>0) | missed (0)
      "checks": [
        { "key": "label_text_visible", "passed": true, "points": 15, "max_points": 15, "metric": "avg_text_blocks", "value": 6.2, "threshold": 5, "note": null },
        { "key": "barcode_read", "passed": true, "points": 15, "max_points": 15, "metric": "barcode_found", "value": true, "threshold": true, "note": null }
      ],
      "notes": [],                           // fail_notes of failed checks
      "evidence": [ { "t_s": 3.2, "kind": "barcode", "image": "evidence/<analysis_uuid>/shipping_label_0.jpg" } ]
    }
    // unboxing (or packing), tags, product …
  ],
  "total_score": 88,
  "confidence": 0.81,
  "status": "pass",                          // pass | review | fail
  "decision": "Accepted",                    // Accepted | Review Required | Rejected
  "caps_applied": [],                        // e.g. ["no_barcode_max_review"]
  "summary": "Accepted after reviewing the return recording. …",
  "timings_ms": { "sampling": 820, "detectors": 14230, "det_quality": 300, "det_motion": 1400, "det_objects": 5100,
                  "det_barcode": 900, "det_ocr": 6530, "scoring": 1, "evidence": 8, "total": 15410 }
}
```

Metric keys (the canonical list is `vms.analysis.metrics.METRIC_KEYS`; rubrics may only reference these):

| Key | Meaning |
|---|---|
| `label_ratio` / `package_ratio` / `tag_ratio` / `product_ratio` | Share of **quality-valid** frames where the signal fired |
| `avg_text_blocks` | Mean EasyOCR text-box count over the frames where OCR ran (0 when OCR is off) |
| `barcode_found` / `barcode_count` | Any / number of distinct decoded barcodes |
| `duration_s` | Video duration |
| `direction_changes` | Settled optical-flow direction changes (hysteresis 2 frames), all sampled frames |
| `motion_ratio` | Share of sampled frames with high motion |
| `estimated_sides` | `clamp(direction_changes + 1 (+2 if motion_ratio > 0.3), 0..6)`, 0 for no frames |
| `end_activity_ratio` | Share of frames in the last 25% of the video with any motion (Forward sealing) |
| `max_label_hold_s` | Longest run of valid frames with label + text visible (OCR count carried forward) |
| `quality_ok_ratio` | Valid frames / sampled frames (used by the low-quality cap) |
| `frames_sampled` | Number of sampled frames |
| `seal_visible_ratio` / `hand_with_product_ratio` / `tag_close_up_ratio` | Share of valid frames with a `seal` box / a `hand` box overlapping a `product` box / a `tag` box covering >= `VMS_TAG_CLOSE_UP_FRAC` of the frame. Need a custom model (Phase 6); 0 otherwise |
| `label_and_barcode_ratio` | Share of valid frames where a label (heuristic or `label` box) and a decoded barcode are both present |

**Detector roles and model cards (Phase 6).** YOLO class names map to roles (`product`, `package`, `label`, `barcode`, `tag`, `seal`, `hand`, `tool`) through `class_map` in `<weights>.model_card.json` (written by `ml/train.py`); without a card, `VMS_YOLO_CLASS_MAP` (COCO stopgap) applies. The active rubric per process type is `VMS_RUBRIC_FORWARD` / `VMS_RUBRIC_RETURN`; `engine.detectors.objects` (weights file) and `rubric_id` in each result record what produced it. Evaluation and calibration code is in `backend/vms/evaluation/`, driven by `ml/evaluate.py` and `ml/calibrate.py`.

Evidence `image` paths are relative to `VMS_DATA_DIR` when the evidence dir is inside it, otherwise relative to the evidence dir itself. `image` is `null` when no evidence dir was given. Steps list their evidence signal kinds in the rubric (`evidence: [barcode, label]`); one entry per step that had a firing signal.

The legacy v1 shape (`scores.{shipping_label,unboxing,tags,product}.{score,notes}`) can be derived from v2. `routers/legacy.py` does this so old `/analyze` clients keep working.

---

## 6. Rubric YAML spec

```yaml
id: return-v1
process_type: Return
title: Return (Unboxing) SOP
decision:
  pass:   { min_score: 85, min_confidence: 0.70 }
  review: { min_score: 50, min_confidence: 0.40 }
caps:                                   # applied after decision; can only downgrade
  - { id: no_barcode_max_review,   when: { metric: barcode_found, op: "==", value: false }, max_status: review }
  - { id: low_quality_max_review,  when: { metric: quality_ok_ratio, op: "<", value: 0.5 }, max_status: review }
  - { id: too_short_fail,          when: { metric: duration_s, op: "<", value: 3 }, max_status: fail }
steps:
  - key: shipping_label
    title: Shipping Label & Barcode
    description: Outer AWB label held clearly toward camera before opening
    checks:
      - { key: label_text_visible, metric: avg_text_blocks, op: ">=", value: 5,   points: 15, fail_note: "No clear text/label detected. Hold label closer." }
      - { key: barcode_read,       metric: barcode_found,   op: "==", value: true, points: 15, fail_note: "Barcode not read. Ensure it is in focus." }
  - key: unboxing
    title: Package Seal & Unboxing
    checks:
      - { key: package_visible, metric: package_ratio,   op: ">=", value: 0.4, points: 6,  fail_note: "Package not consistently visible." }
      - { key: six_sides,       metric: estimated_sides, op: ">=", value: 6,   points: 10, fail_note: "Show all 6 sides before opening.",
          partial: [ { op: ">=", value: 4, points: 6 }, { op: ">=", value: 2, points: 3 } ] }
      - { key: long_enough,     metric: duration_s,      op: ">=", value: 10,  points: 4,  fail_note: "Video too short for full process." }
  # tags, product …
```

Rules: a step's `weight` = the sum of its checks' max `points`. Weights across all steps must add up to 100 (the loader validates this). The `op` set is `>= > <= < == !=`. `partial` tiers are tried in order when the main check fails. An unknown metric is a load-time error in tests and counts as a failed check at runtime, logged as a warning. Rubric changes need a new `id` (`return-v2`) so historical analyses stay explainable.

---

## 7. Data model (SQLAlchemy, Phase 2+3)

```
warehouses(id, code UNIQUE, name, created_at)
stations(id, warehouse_id FK, code, name, UNIQUE(warehouse_id, code))
users(id, email UNIQUE, name, password_hash, role ENUM(operator|reviewer|admin), warehouse_id FK NULL,
      is_active, created_at, last_login_at)
api_keys(id, name, key_hash, created_by FK users, created_at, revoked_at)
videos(id, uuid UNIQUE, original_filename, storage_key, sha256, size_bytes, content_type,
       process_type ENUM(Forward|Return), awb NULL, order_ref NULL,
       uploaded_by FK users NULL, api_key_id FK api_keys NULL (Phase 3), station_id FK NULL, source ENUM(web|api|legacy),
       duration_s NULL, created_at, deleted_at NULL,   -- soft delete (Phase 2)
       final_status ENUM(pending|pass|review|fail) -- denormalized: review override > latest analysis
       INDEX(awb), INDEX(created_at), INDEX(final_status), INDEX(sha256))
jobs(id, video_id FK, status ENUM(queued|running|done|failed), attempts, max_attempts=3,
     progress REAL 0..1, error TEXT NULL, worker_id NULL, created_at, started_at, finished_at, heartbeat_at)
analyses(id, uuid, video_id FK, job_id FK NULL, schema_version, engine_version, rubric_id,
         total_score, confidence, status, decision,
         barcodes TEXT,                      -- space-separated decoded values, for `GET /videos?q=`
         result_json JSON, created_at)       -- job_id NULL only for legacy imports
evidence(id, analysis_id FK, step_key, kind, t_s, storage_key, created_at)
reviews(id, analysis_id FK, video_id FK, reviewer_id FK, final_status ENUM(pass|fail), reason_code,
        comment, created_at)                 -- latest review per video wins
audit_log(id, actor_user_id NULL, actor_api_key_id NULL, action, entity_type, entity_id, data JSON, created_at)
```

Phase 2 notes: enums are stored as strings with CHECK constraints (no native Postgres enums). Timestamps are naive UTC; the API serializes them with a trailing `Z`. `videos.sha256` is indexed, not unique (legacy rows have none; dedupe happens in `services.videos`). Legacy imports have `storage_key`/`sha256` NULL and `source=legacy`; their analyses use `schema_version "1.0"`, `rubric_id "legacy-v1"`. The migration seeds the `system@vms.local` admin that stubbed auth uses.

Job claiming must be atomic: `UPDATE jobs SET status='running', worker_id=:w, started_at=now WHERE id = (SELECT id FROM jobs WHERE status='queued' ORDER BY id LIMIT 1) AND status='queued'`, then check the rowcount. A job stuck `running` with `heartbeat_at` older than 5 min gets re-queued if `attempts < max_attempts`, otherwise marked `failed`.

Review reason codes: `label_unclear`, `seal_not_shown`, `tags_not_shown`, `product_not_inspected`, `video_quality`, `false_negative_model` (the model was wrong and the operator was compliant), `other`.

---

## 8. API contract (`/api/v1`)

| Method & path | Role | Notes |
|---|---|---|
| `GET /health` | public | `{status, version, db, detectors}` |
| `POST /auth/login` | public | `{email, password}` → `{access_token, token_type, user}` |
| `GET /auth/me` | any user (API keys get 403) | |
| `POST /auth/change-password` | any user | `{current_password, new_password}` → 204 |
| `POST /videos` | operator+ / api key | multipart `file`, `process_type`, optional `awb`, `order_ref`, `station_id`. Streams to storage (no full read into memory). Size limit `VMS_MAX_UPLOAD_MB` (default 500). Dedupes on sha256 (returns the existing video with `duplicate: true`). → `201 {video, job}` |
| `GET /videos` | operator+ | filters: `status, process_type, awb, q, station_id, uploaded_by, date_from, date_to`, paging, `sort`. Operators see only their own uploads, reviewers and admins see all. |
| `GET /videos/{id}` | operator+ | video + latest analysis (full result) + reviews (with `reviewer_name`) + job. `VideoOut.human_reviewed` (Phase 5) flags a reviewer override in lists |
| `GET /videos/{id}/stream` | operator+, or a signed URL | HTTP Range support for the `<video>` player. `stream_url` in responses is signed (`?exp=&sig=`, HMAC with the JWT secret, `VMS_MEDIA_URL_TTL_S`, default 6 h) so media tags work without headers |
| `POST /videos/{id}/reanalyze` | reviewer+ | new job (for example after a rubric or model upgrade) |
| `DELETE /videos/{id}` | admin | soft delete + audit_log |
| `GET /jobs/{id}` | operator+ | `{status, progress, error}` |
| `GET /evidence/{id}` | operator+, or a signed URL | JPEG; evidence `url`s are signed like `stream_url` |
| `GET /review-queue` | reviewer+ | videos with `final_status=review`, oldest first; filters `process_type, station_id`; paginated `Page[VideoOut]` |
| `POST /videos/{id}/reviews` | reviewer+ (users only) | `{final_status: pass|fail, reason_code, comment}` → 201 `ReviewOut`. Judges the latest analysis; 409 if none. `comment` required (422) for `other` or when overturning a model `pass`/`fail`. Append-only; latest wins (`videos.final_status`); audit `review.created` |
| `GET /reports/summary` | reviewer+ | `date_from, date_to` (local dates, default last 7 days, max 1 year), `group_by=day|station|operator|process_type`, `process_type, station_id, tz_offset_min` (minutes east of UTC) → totals by final status, `analyzed`, `pass_rate`, `review_rate`, `reviewed`, `agreement_rate` + `agreement_n`, `avg_score`, `avg_turnaround_s`, `top_failed_checks[10]`, `groups[]` (day groups are gap-filled). Definitions in `services/reports.py` `summarize()` |
| `GET /reports/export.csv` | reviewer+ | same filters as `GET /videos` + `tz_offset_min`; streamed UTF-8 **with BOM**, oldest first. Columns: the Streamlit CSV (Timestamp, File, Process Type, Verdict, Manual Summary, Score %, `<step title> %` for every active rubric step, Sides, Duration (s), Follow-up Notes) + AWB, Station, Operator, Final Status, Reviewer, Review Reason, Review Comment |
| `GET/POST /admin/users`, `PATCH /admin/users/{id}` | admin | PATCH: `name, role, warehouse_id, is_active, password` (only sent fields). Admins can't demote/deactivate themselves. |
| `GET/POST /admin/stations`, `/admin/warehouses` | admin | |
| `GET/POST /admin/api-keys`, `DELETE /admin/api-keys/{id}` | admin | the key is shown once on creation; DELETE revokes |
| `GET /admin/audit-log` | admin | filters `action` (prefix), `entity_type, entity_id, actor_user_id, actor_api_key_id, date_from, date_to`; paginated, newest first |
| `GET /rubrics` | any | active rubrics (for UI step labels and descriptions) |
| `GET /stations` | any | all stations, for the upload form (Phase 4) |
| `POST /analyze`, `GET /results` (root, legacy) | api key only | Scoped to the key's own uploads. Phase 2 compatibility shim. Synchronous, returns the v1 shape. Deprecated in Phase 7. |

Auth header: `Authorization: Bearer <jwt>` or `X-API-Key: <key>`. Phase 3: `deps.get_current_principal` resolves either; an API key acts as an `operator` (uploads get `source=api`, `api_key_id`) and sees only its own uploads. Operators see only their own uploads (403 on others' videos, streams, jobs, evidence). Login is rate limited: 10 failures per email+IP per 15 min → 429. Every route except `/health` and `/auth/login` returns 401 without credentials.

---

## 9. Frontend pages (Phase 4–5)

`/login` · `/` dashboard (today's counts, pass rate, review queue size, recent uploads) · `/upload` (drag-and-drop multi-file, process type, AWB, station; per-file progress, then job status) · `/videos` (filterable table) · `/videos/:id` (player + evidence timeline; click a step or evidence to seek; step cards; checks table; review panel) · `/review` (queue with keyboard shortcuts: P = pass, F = fail, N = next) · `/reports` (charts + CSV export) · `/admin` (users, stations, API keys).

---

## 10. Non-functional requirements

- An analysis of a 60 s 720p video takes under 60 s on a 4-core CPU with OCR on. Uploads return in under 2 s after the transfer finishes (analysis is async).
- No upload ever crashes the API. Corrupt videos produce a `failed` job with a readable error.
- Re-analysis is deterministic for the same video, rubric, and model versions.
- Every state change (upload, analysis, review, delete, user change) writes to `audit_log`.
- Secrets come only from env. Passwords are hashed with argon2. JWTs expire in 12 h.

## 11. Open questions (ask the user; record answers in PROGRESS.md → Decisions)

1. Is there an official written SOP document? The rubric above is inferred from `app.py` text.
2. Real sample videos: how many, and can a labeled set (with human pass/fail per step) be prepared for Phase 6 calibration?
3. Will a GPU be available in production? (This affects OCR and YOLO cadence.)
4. Deployment target: on-prem server, or a cloud VM? Is S3 storage needed? What's the video retention period?
5. Integrations: which systems will call the API (WMS, returns portal)? Do they need webhooks when analysis completes?
