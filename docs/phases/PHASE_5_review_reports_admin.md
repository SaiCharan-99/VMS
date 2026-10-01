# Phase 5 — Review Workflow, Reports & Admin

**Goal:** Close the loop. Reviewers clear the `review` queue with reasons, managers see compliance analytics and export reports, and admins manage users, stations, and API keys from the UI.

**Read:** `docs/UI_DESIGN.md` §4–6 + `docs/ui/mockup.html` (Review queue screen), IMPLEMENTATION.md §7 (reviews, reason codes, audit_log), §8 (review, report, and admin routes), §9.
**Branch:** `phase-5-review-reports-admin`

## Tasks

### Backend
- [ ] `services/reviews.py`: create a review (pass/fail + reason_code + comment; `comment` is required when `reason_code=other` or when the reviewer's decision contradicts a model `pass`/`fail`). Update `videos.final_status`. Write to the audit log. Reviews are append-only, and the latest one wins.
- [ ] `GET /review-queue` (oldest first, filters by process_type and station) and `POST /videos/{id}/reviews`. Add `GET /videos/{id}` → `reviews[]` history.
- [ ] `services/reports.py` + `GET /reports/summary`: totals by status, pass rate (final), auto-vs-human agreement rate, avg score, avg turnaround (upload → final), and the **top failed checks** (aggregate from `result_json` steps/checks; precompute an `analysis_checks` table or a JSON query that works on SQLite + Postgres). Put a time series in `group_by=day`.
- [ ] `GET /reports/export.csv`: same columns as the old Streamlit CSV (Timestamp, File, Process Type, Verdict, Manual Summary, Score %, per-step %, Sides, Duration, Follow-up Notes) plus AWB, Station, Operator, Final Status, Reviewer, and Review Reason. Stream it for large ranges.
- [ ] Optional PDF of a single video report (`GET /videos/{id}/report.pdf`, using reportlab or weasyprint) holding verdict, steps, and evidence images. This is the artifact attached to a customer dispute. Treat it as a stretch goal and say so in PROGRESS.md if skipped.
- [ ] Tests for the review rules, report math on seeded fixtures, and CSV columns.

### Frontend
- [ ] `/review`: queue list plus a focused review view (reuses the video detail). Pass/Fail buttons, reason select, comment, and keyboard shortcuts (P, F, N, J/K seek ±5 s). Optimistic advance to the next item.
- [ ] Review history panel on `/videos/:id`, with a human-override badge in lists.
- [ ] `/reports`: date-range picker, KPI tiles (volume, pass rate, review rate, agreement), a stacked bar of status per day, top-10 failed checks (horizontal bar), a breakdown table by station and operator, and a CSV export button. Use Recharts. Follow the `dataviz` skill guidance for colours and accessibility.
- [ ] Dashboard `/`: add 7-day trend sparkline + pass-rate tile.
- [ ] `/admin`: tabs for Users (create, role, deactivate, reset password), Warehouses & Stations, API Keys (create → show once with a copy button, revoke), and Audit Log (filterable table).
- [ ] `docs/SOP.md`: plain-language explanation for operators of what the system checks per step and how to film so it passes (generate it from the rubric YAML descriptions + fail notes).

## Acceptance criteria

1. A reviewer can clear 10 queued videos using only the keyboard. Each one shows the reviewer's decision and reason in history and the audit log.
2. Report numbers match a hand calculation on the seeded test fixture (a backend test asserts this).
3. The CSV opens correctly in Excel (UTF-8 BOM) and includes the review columns.
4. An admin can create an operator who can then log in and upload.
5. All backend and frontend checks are green.
6. The new screens use only the Phase 4 UI primitives and tokens (no raw hex, no one-off buttons), and they pass the same responsive and accessibility checks as Phase 4.

## Handoff notes

The current agreement rate on any real data, and the most-failed checks. These feed Phase 6 priorities.
