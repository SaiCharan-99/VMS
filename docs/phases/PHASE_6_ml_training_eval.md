# Phase 6 — Custom Detector Training & Accuracy Evaluation

**Goal:** Measure how accurate the analyzer really is against human judgement. Then improve it by training a YOLOv8 model on VMS footage and calibrating rubric thresholds against that data. This phase needs **real sample videos** from the user. If none are available, build the full tooling, run it on synthetic data, and record the blocker.

**Read:** IMPLEMENTATION.md §1, §5, §6. Read PROGRESS.md handoff notes from Phases 1 and 5 for known weaknesses and most-failed checks.
**Branch:** `phase-6-ml`

## Tasks

### Evaluation harness (do this first: you can't improve what you can't measure)
- [ ] `ml/eval_labels.example.csv`: `video_path,process_type,expected_status,shipping_label,unboxing,tags,product,notes`, with per-step `met|partial|missed` as judged by a human.
- [ ] `ml/evaluate.py --labels data/eval/labels.csv --rubric return-v1 [--weights path]` runs the pipeline on each video and writes `data/eval/report_<timestamp>.{json,md}`: confusion matrix for status, per-step accuracy, **false-pass rate** (the critical metric: a bad video marked pass), review rate, and runtime per video. Cache per-video metrics so re-scoring with a different rubric skips CV re-runs (`--from-cache`).
- [ ] Export labels from the app: `GET /reports/export.csv?format=eval` or a CLI that turns human reviews (Phase 5) into an eval labels file. Every reviewed video becomes training and eval data.

### Data & training
- [ ] `ml/extract_frames.py`: add `--every-seconds`, `--max-per-video`, and dedupe of near-identical frames (perceptual hash), and output to `data/frames/<video>/`.
- [ ] `ml/dataset/README.md`: annotation guide. Classes: `shipping_label`, `barcode`, `brand_tag`, `hangtag`, `product`, `package_box`, `package_polybag`, `seal_tape`, `hand`, `scissors_cutter`. Include examples of what counts. Recommend CVAT or Roboflow, export as YOLO format, and say how many images per class to aim for (≥300).
- [ ] `ml/data.yaml` template and `ml/train.py` (wraps `ultralytics` train: model size, epochs, imgsz=640, device auto; writes to `data/models/<run>/`, then copies `best.pt` → `data/models/vms-det-<date>.pt` + a `model_card.json` with metrics, classes, and data hash).
- [ ] Wire custom classes into `detectors/objects.py` through `settings.yolo_weights` + a class map loaded from `model_card.json` (no code change to switch models). Run YOLO every k-th valid frame and on frames flagged by heuristics.
- [ ] New metrics enabled by custom classes: `seal_visible_ratio`, `hand_with_product_ratio`, `tag_close_up` (tag bbox area > X% of frame), and `label_and_barcode_same_frame`. Add them to the rubrics as **new rubric ids** (`forward-v2`, `return-v2`) and leave v1 untouched.
- [ ] Better side counting (optional): track the package bbox and estimate rotation from changes in the box face (aspect ratio, colour histogram) instead of raw flow direction changes. Compare against v1 on the eval set and keep the winner.

### Calibration
- [ ] `ml/calibrate.py`: grid-search key rubric thresholds and decision cutoffs on cached metrics to **minimise false-pass rate first**, then the review rate. Outputs a suggested YAML diff. Never auto-apply; a human copies it into a new rubric version.
- [ ] Set the active rubric per process type through settings (`VMS_RUBRIC_FORWARD=forward-v2`).

## Acceptance criteria

1. `python ml/evaluate.py --labels ml/eval_labels.example.csv` runs end to end on synthetic fixtures in CI-size time.
2. With real data: the eval report is committed to `docs/eval/` (metrics only, no videos). v2 shows a false-pass rate ≤ v1, and the numbers go in PROGRESS.md.
3. Switching model weights or the rubric is config-only, and `reanalyze` uses the new versions (`engine.detectors.objects` and `rubric_id` in the result show this).
4. Model weights and data are not committed.

## Handoff notes

Dataset size per class, mAP, eval numbers v1 vs v2, chosen thresholds, and the recommended production rubric ids.
