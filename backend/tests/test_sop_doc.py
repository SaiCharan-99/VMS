from pathlib import Path

from vms.analysis.rubric import active_rubric_ids, get_rubric
from vms.sop_doc import WHAT_IT_LOOKS_FOR, render

SOP_MD = Path(__file__).resolve().parents[2] / "docs" / "SOP.md"


def test_every_check_is_explained():
    text = render()
    for rubric_id in active_rubric_ids().values():
        rubric = get_rubric(rubric_id)
        assert rubric.title in text
        for step in rubric.steps:
            assert step.title in text
            for check in step.checks:
                assert check.key in WHAT_IT_LOOKS_FOR, f"add plain wording for {check.key}"
                assert check.fail_note in text


def test_committed_sop_is_up_to_date():
    assert SOP_MD.read_text(encoding="utf-8") == render(), (
        "docs/SOP.md is stale: run `python -m vms.cli sop-doc --out docs/SOP.md`"
    )
