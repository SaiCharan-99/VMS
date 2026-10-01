# VMS evaluation report

- Generated: 2026-10-01 17:25 UTC
- Labels: `labels.csv` (2 videos)
- Rubrics: `forward-v1`, `return-v1`
- Detectors: `{'ocr': True, 'barcode': True, 'objects': 'yolov8n.pt', 'motion': True}`

## Headline

- **False-pass rate: n/a** (0 video(s) a human did not pass were marked pass)
- Against human `fail` only: n/a
- False-fail rate (compliant video marked fail): 0.0%
- Review rate: 100.0%
- Status accuracy: 0.0%
- Runtime per video: mean 41300 ms, max 56259 ms

## Confusion matrix (rows = human, columns = model)

| human / model | pass | review | fail |
|---|---|---|---|
| pass | 0 | 2 | 0 |
| review | 0 | 0 | 0 |
| fail | 0 | 0 | 0 |
