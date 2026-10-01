# UI_DESIGN.md — VMS Inspect Design Spec

The frontend (Phases 4–5) must match this spec and the reference mockup **`docs/ui/mockup.html`**. Open the mockup in a browser: it is clickable (Dashboard, Upload, Inspections, inspection detail, Review queue) and supports a light/dark toggle. When the spec and the mockup disagree, the spec wins. Record any deliberate deviations in PROGRESS.md → Decisions.

## 1. Principles

1. **The verdict comes first.** Every inspection shows its status badge and score before anything else. Explanations come second, and raw metrics come last (collapsed).
2. **Calm by default, colour means something.** The interface is neutral greys plus one blue accent. Green, amber, and red are used **only** for pass / review / fail. Never use them for decoration.
3. **Evidence is one click away.** Every failed or passed check links to the moment in the video that proves it (timeline markers and evidence thumbnails seek the player).
4. **Built for repetitive work.** Reviewers can clear the queue with the keyboard alone. Tables are dense but readable. Filters persist in the URL.
5. **Plain language.** Use "Barcode not read. Hold it steady in focus." Never use "barcode_found=false". Metric keys appear only in the expanded checks table.
6. **Light theme by default, with a full dark theme.** Warehouse screens are often in bright light. Dark follows the OS and has a manual toggle.

## 2. Design tokens

Implement these as CSS variables in `src/styles/tokens.css` and map them into `tailwind.config.ts` (`colors.surface`, `colors.pass`, …). Components use the tokens, never raw hex values.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#f7f8fa` | `#0c0e12` | app background |
| `--surface` | `#ffffff` | `#14171c` | cards, sidebar, top bar |
| `--surface-2` | `#f1f3f6` | `#1b1f26` | table header, hover, inputs, bar tracks |
| `--border` / `--border-strong` | `#e4e7ec` / `#d0d5dd` | `#262b33` / `#333a44` | dividers / inputs and buttons |
| `--text` / `--text-2` / `--text-3` | `#101828` / `#475467` / `#98a2b3` | `#eef0f3` / `#a3abb8` / `#6b7380` | primary / secondary / hint |
| `--accent` (+`-soft`, `-text`) | `#2f5bea` | `#6b8cff` | primary buttons, active nav, focus ring, progress |
| `--pass` (+`-soft`) | `#12805c` / `#e7f6ef` | `#3ccb8f` / `#10291f` | Accepted |
| `--review` (+`-soft`) | `#b54708` / `#fef4e6` | `#f2a443` / `#2e2112` | Review required |
| `--fail` (+`-soft`) | `#c0262d` / `#fdeceb` | `#f2686e` / `#2f1517` | Rejected |

- **Type:** Inter (400/500/600/700). Use JetBrains Mono for AWBs, barcodes, filenames, and timestamps. Base 14px/1.5. Page title 16px/600. KPI value 26px/600 with tabular numbers. Labels 12–12.5px.
- **Spacing:** a 4px scale. Card padding 16–18px, page gutter 28px on desktop and 16px on mobile, gaps of 16px between cards.
- **Shape:** radius 10px for cards and 6px for controls. Badges are pills. Light mode uses a 1px border plus a very faint shadow, and dark mode uses the border only.
- **Focus:** a visible 2px `--accent` ring on every interactive element. Text contrast must be at least 4.5:1 (WCAG AA).

## 3. Layout

- **App shell:** a fixed 232px sidebar (logo, nav, user block at the bottom) and a 60px top bar (page title, global search for AWB/barcode/file, theme toggle, primary "Upload videos" button). Content max width is 1280px.
- **Nav:** Dashboard, Upload, Inspections, Review queue (amber count badge), Reports, Admin. Items are hidden by role (operators see Dashboard, Upload, and Inspections only).
- **Responsive:** below 1000px, two-column pages stack. Below 760px, the sidebar becomes a horizontally scrolling top nav, secondary table columns are hidden, and the page must never scroll horizontally.

## 4. Components (build these in `src/components/ui/`, with tests)

| Component | Spec |
|---|---|
| `Button` | variants `primary`, `secondary` (default), `pass`, `fail`, `ghost`. Sizes sm and md. Supports a loading state. |
| `StatusBadge` | pill with a dot. `pass`→"Pass"/"Accepted", `review`→"Review", `fail`→"Fail", `pending`→"Analyzing" (neutral). Shows a small "human" icon when a reviewer overrode the result. |
| `ScoreRing` | 76px conic ring coloured by status, with the score in the centre. |
| `Card` (+`CardHeader`) | surface + border + radius. The header has a title on the left and actions on the right. |
| `KpiTile` | label, big value, delta (green for an improvement, red for a regression; "pass rate down" is red). |
| `DataTable` | sticky header, row hover, clickable rows, right-aligned tabular numbers, skeleton rows while loading, empty state with an icon + message + action. |
| `FilterBar` | segmented status control + selects + date range. State syncs to URL query params. |
| `StepCard` | numbered circle (status colour), title, points `x/y`, rubric description (hint colour), progress bar, check list (✓ in green, ! in amber, with a plain-language note), evidence thumbnails with timestamps. An expandable "Details" table shows metric / value / threshold. |
| `EvidenceTimeline` | track under the player with numbered markers (step number, step status colour) at evidence timestamps. Clicking a marker seeks the video, and hovering shows the step + check. |
| `VideoPlayer` | native `<video>` with custom minimal controls. Exposes `seek(t)`. Keyboard: Space, J/K (±5 s). |
| `UploadQueue` | per-file row: name, size, type · progress bar (grey = uploading, blue = analyzing, status colour = done) · state text or result badge. |
| `ReviewBar` | sticky bottom bar: reason select, comment, Fail and Pass buttons with key hints. |
| `Toast`, `Dialog`, `Skeleton`, `EmptyState`, `Kbd` | standard. Dialogs trap focus. |

Icons: `lucide-react`, 16–18px, stroke 1.8.

## 5. Screens

| Screen | Must have |
|---|---|
| **Login** | Centred card, logo, email + password, and the error shown inline. Nothing else. |
| **Dashboard** | 4 KPI tiles (inspected today, pass rate, awaiting review, model–reviewer agreement), a 7-day stacked outcome chart, a most-missed SOP checks bar list, and a recent inspections table. Operators see their own numbers. |
| **Upload** | Drop zone (formats + limit) on the left, and a settings card on the right (Forward/Return segmented control, station, optional AWB "auto-detected from barcode", filming tips). The batch list below shows live progress through to the result badge. Each finished row links to its inspection. |
| **Inspections** | FilterBar + table (thumbnail, file, AWB, type chip, operator, uploaded, score, status) + pagination + Export CSV. |
| **Inspection detail** | Header: back link, filename, type chip, Re-analyze, Download report. Left: player + evidence timeline. Right: verdict card (score ring, badge, one-sentence summary, confidence / AWB / frames OK) and then the four StepCards. Review history appears below the steps when present. |
| **Review queue** | A list on the left (oldest first, score badge, age), and the focused item on the right (player, verdict, steps) with a sticky ReviewBar. After a decision, it moves to the next item automatically. |
| **Reports** | Date range, KPI tiles, outcome-per-day chart, top failed checks, station/operator breakdown table, CSV export. Follow the `dataviz` skill for charts: status colours for status series and the accent for everything else. |
| **Admin** | Tabs for Users, Warehouses & Stations, API Keys (show once + copy), and Audit Log. Simple tables + dialogs. |

## 6. States & copy

- Every data view has **loading** (skeletons, not spinners, for tables and cards), **empty** ("No inspections yet. Upload your first video."), and **error** (message + Retry) states.
- Analysis in progress: "Analyzing 58%" with a small spinner. Failed job: "Couldn't analyze this video" + reason + Re-analyze.
- Times are relative within 24 h ("12 min ago") and absolute after that. Durations look like `0:42`. Scores are integers.
- Use the verdict labels **Accepted / Review required / Rejected** on detail pages and **Pass / Review / Fail** in compact lists.
