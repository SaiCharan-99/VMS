# VMS evaluation report

- Generated: 2026-10-01 17:10 UTC
- Labels: `eval_labels.example.csv` (6 videos)
- Rubrics: `forward-v1`, `return-v1`
- Detectors: `{'ocr': True, 'barcode': True, 'objects': 'yolov8n.pt', 'motion': True}`

## Headline

- **False-pass rate: 0.0%** (0 video(s) a human did not pass were marked pass)
- Against human `fail` only: 0.0%
- False-fail rate (compliant video marked fail): n/a
- Review rate: 50.0%
- Status accuracy: 100.0%
- Runtime per video: mean 7517 ms, max 19945 ms

## Confusion matrix (rows = human, columns = model)

| human / model | pass | review | fail |
|---|---|---|---|
| pass | 0 | 0 | 0 |
| review | 0 | 3 | 0 |
| fail | 0 | 0 | 3 |

## Per-step accuracy

| step | labelled | accuracy | marked met but not met |
|---|---|---|---|
| shipping_label | 6 | 66.7% | 0 |
| unboxing | 6 | 0.0% | 0 |
| tags | 6 | 33.3% | 0 |
| product | 6 | 33.3% | 1 |
