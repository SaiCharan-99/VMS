"""Score labelled videos with the analyzer and report accuracy against human judgement.

python ml/evaluate.py --labels data/eval/labels.csv --rubric return-v1 [--weights path]
python ml/evaluate.py --labels data/eval/labels.csv --rubric return-v2 --from-cache
"""

from vms.evaluation.cli import evaluate_main

if __name__ == "__main__":
    raise SystemExit(evaluate_main())
