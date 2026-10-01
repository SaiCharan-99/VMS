# Phase 1 — Analysis Engine v2

**Goal:** Replace the monolithic heuristic analyzer with a modular pipeline. Detectors produce per-frame signals, metrics aggregate them, YAML rubrics score the metrics, and the output is the versioned `AnalysisResult` with evidence frames. Forward and Return are scored differently again.

**Read:** IMPLEMENTATION.md §1 (rubric), §5 (result contract), §6 (rubric spec), §10 (performance).
**Branch:** `phase-1-analysis-engine`

## Design

```
sampling.sample(path, fps) ─▶ iter[Frame(idx, t_s, bgr, gray)]
        │
        ▼ per frame (quality gate first; rejected frames only feed quality stats)
detectors: quality · barcode · ocr (every k-th valid frame) · objects (YOLO or heuristics fallback) · motion (needs prev frame)
        │  FrameSignals(t_s, valid, blur, brightness, text_blocks, barcodes[], label, package, tag, product, motion_dir, motion_mag, boxes[])
        ▼
metrics.aggregate(signals) ─▶ dict[str, float|int|bool]      (keys listed in IMPLEMENTATION §5)
rubric.evaluate(rubric, metrics) ─▶ steps[], total_score
confidence.compute(quality, metrics) ─▶ 0..1
rubric.decide(total, confidence) + caps ─▶ status/decision/caps_applied
evidence.select(signals, steps) ─▶ best frame per step (sharpest frame where the step's signal fired) → saved JPEGs
summary.render(result) ─▶ reviewer-style sentence (port app.py manual_summary)
```

- `Detector` protocol: `name`, `available: bool`, `process(frame, ctx) -> partial signals`. The objects detector uses YOLO when `settings.yolo_enabled` is set and weights load. Otherwise it uses `heuristics.py` (the current contour logic). With COCO `yolov8n.pt`, map COCO classes as a stopgap (for example `handbag`, `backpack`, `suitcase`, `tie`, and clothing-ish classes → product; `book` or `cell phone` → *not* product). Custom classes arrive in Phase 6, so keep a `class_map` in config.
- Motion: Farneback optical flow on a downscaled gray frame gives dominant direction and magnitude. Count direction changes with hysteresis. `estimated_sides = clamp(direction_changes + 1 (+2 if motion_ratio>0.3), 0..6)`, ported from the old code. Keep it isolated so Phase 6 can replace it.
- `max_label_hold_s`: the longest continuous run of frames with label + text visible (this finally uses `min_hold_sec`).
- `analyze_video(path, process_type, *, settings=None, evidence_dir=None, progress_cb=None) -> AnalysisResult`. `progress_cb(float)` is called during sampling and detection (the worker uses it in Phase 2).
- Keep `VMSSOPAnalyzer.analyze()` as a thin wrapper returning the **v1 dict** derived from v2 (`result.to_v1()`), so `app.py` and `/analyze` keep working.

## Tasks

- [ ] `result.py`: Pydantic models for the §5 schema, plus `to_v1()`.
- [ ] `rubric.py`: load and validate YAML (weights add to 100, ops valid, metrics known), `evaluate`, `decide`, caps. Write `forward-v1.yaml` and `return-v1.yaml`, carrying over the current thresholds. Forward step 2 = "Packing & Sealing" (package visible, sealing motion near the end, i.e. high motion in the last 25% of the video, duration). Return step 2 includes `six_sides` with partial tiers.
- [ ] `sampling.py`, `detectors/*`, `metrics.py`, `confidence.py`, `evidence.py`, `pipeline.py`.
- [ ] Barcode: collect **all** distinct barcodes with `first_seen_s` and `frames_seen`, using decode candidates (original, equalized, 2× upscale, adaptive threshold). Stop retrying expensive variants once a code has been seen 3 times.
- [ ] Performance: OCR every `ocr_every_n` valid frames (default 3) and on frames where the label heuristic fires. Record `timings_ms`.
- [ ] `vms/cli.py analyze <video> --process-type Return [--json out.json] [--evidence-dir dir]`.
- [ ] Update `app.py` to render steps from the rubric through the v2 result (step titles and descriptions come from the YAML, not hard-coded lists).
- [ ] Tests (fast suite, models off):
  - Rubric: weight validation, each op, partial tiers, caps can only downgrade, unknown metric raises at load.
  - Metrics on hand-built `FrameSignals` lists (no video needed).
  - Pipeline on synthetic videos: QR video → `barcode_found`; dark or blurry video → caps to at most review; empty or very short video → fail with score 0; moving-box video → `direction_changes > 0`; Forward and Return produce different `rubric_id` and step-2 titles.
  - Determinism: the same video analysed twice produces an identical result, apart from timings.
  - Evidence: files written, paths are relative, one entry per step that has a firing signal.
  - `to_v1()` round-trip keeps the old keys (`scores.shipping_label.score`, …).

## Acceptance criteria

1. `python -m vms.cli analyze sample.mp4 --process-type Forward --json out.json` produces a schema-valid v2 result with evidence JPEGs.
2. Changing a threshold in YAML changes the score with no code change.
3. A missing barcode or quality ok_ratio < 0.5 can never yield `pass` (covered by tests).
4. Fast suite stays under 60 s. A 60 s 720p video runs in under 60 s with OCR on (record the measured number in PROGRESS.md).
5. `app.py` and `/analyze` still work.

## Out of scope

DB persistence, async jobs, and training custom models.

## Handoff notes

The metric keys list (if it changed, update IMPLEMENTATION.md §5), measured timings, known heuristic weaknesses to target in Phase 6.
