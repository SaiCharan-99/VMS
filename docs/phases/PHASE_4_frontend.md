# Phase 4 — Web Frontend (Core)

**Goal:** A React app that replaces Streamlit for the core flow: log in, upload videos, watch analysis progress, browse videos, and inspect a result with its evidence next to the video.

**Read:** IMPLEMENTATION.md §5 (result contract → TS types), §8 (API), §9 (pages). Look at `app.py` for the existing visual language (dark theme, verdict badges, step cards with progress bars). Keep that look.
**Branch:** `phase-4-frontend`

## Tasks

- [ ] Scaffold `frontend/`: Vite + React 18 + TypeScript (strict), Tailwind, React Router, TanStack Query, `zod` for runtime validation of API responses, ESLint + Prettier, Vitest + Testing Library. Dev proxy `/api` → `http://localhost:8000`.
- [ ] `src/api/client.ts`: fetch wrapper (base URL from `VITE_API_URL`, bearer token, 401 → logout and redirect, typed errors). `src/types/`: `analysis.ts` (mirrors §5), `api.ts`.
- [ ] Auth: `/login` page, token in memory + `localStorage` (try/catch), `AuthProvider`, `RequireRole` route guard. Nav items depend on role.
- [ ] Layout: sidebar nav, top bar with user menu, dark theme plus a light toggle, responsive down to tablet width.
- [ ] `/upload`: drag-and-drop multi-file, process type (Forward/Return) selector, optional AWB, order ref, and station. Uploads are concurrent (at most 2) with XHR progress bars. Each item then shows job status by polling `/jobs/{id}` every 2 s until done or failed, and links to the result. Shows the compression tips from `app.py`.
- [ ] `/videos`: table with filters (status, process type, date range, AWB/search), URL-synced query params, pagination, and status badges.
- [ ] `/videos/:id`: left side is a `<video>` player (`/stream`) with a timeline strip of evidence markers (click → seek). Right side is a verdict badge, big score, confidence, step cards (rubric title, description, percentage bar, points, notes; expanding shows the checks table with metric/value/threshold), barcodes found, quality stats, and the summary text. There's a "Re-analyze" button for reviewer+. Evidence thumbnails sit under each step.
- [ ] `/` dashboard v1: today's counts by status, recent uploads, and the review queue count. Charts come in Phase 5.
- [ ] Empty, loading, and error states everywhere.
- [ ] Backend support if missing: `GET /rubrics`, evidence URLs in the video detail, and CORS for `localhost:5173`.
- [ ] Tests: components (StepCard, VerdictBadge, upload queue reducer), API client error handling, and a page render with mocked fetch (MSW).
- [ ] Update CLAUDE.md commands and the README. Mark Streamlit `app.py` as deprecated in the README (it gets deleted in Phase 7).

## Acceptance criteria

1. Fresh clone: `npm install && npm run dev` with API + worker running. Log in as the seeded operator, upload 3 videos, watch them reach a verdict, open one, and click an evidence marker to seek the video.
2. `npm run build`, `npm run lint`, `npm test`, and `tsc --noEmit` are all clean.
3. An operator can't see the Re-analyze button or other users' videos (enforced by the API, reflected in the UI).
4. No horizontal scroll at 768 px width.

## Out of scope

Review actions, reports and charts, admin screens (Phase 5).

## Handoff notes

Component inventory, how the TS types are kept in sync with the backend (manual for now; consider openapi-typescript in Phase 7), and screenshots or notes on the UX decisions.
