"""Suggest rubric thresholds that minimise the false-pass rate, then the review rate.

    python ml/calibrate.py --labels data/eval/labels.csv --rubric return-v2

Prints a YAML diff and never changes a rubric. Uses cached metrics (run ml/evaluate.py first).
"""

from vms.evaluation.cli import calibrate_main

if __name__ == "__main__":
    raise SystemExit(calibrate_main())
