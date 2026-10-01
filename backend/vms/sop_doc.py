"""Render docs/SOP.md (the operator guide) from the active rubric YAML.

Regenerate after any rubric change: `python -m vms.cli sop-doc --out docs/SOP.md`.
A test fails when the committed file is out of date.
"""

from vms.analysis.rubric import Check, Rubric, active_rubric_ids, get_rubric

# What each check looks for, in words an operator can act on. Thresholds come from the YAML.
WHAT_IT_LOOKS_FOR = {
    "label_text_visible": "Readable printed text on the label",
    "label_held": "The label held still in view",
    "barcode_read": "The AWB barcode decoded by the system",
    "package_visible": "The parcel visible for most of the video",
    "sealing_motion": "Sealing activity in the last part of the video",
    "six_sides": "All six sides of the parcel turned toward the camera",
    "long_enough": "A recording long enough to show the whole process",
    "tag_visible": "Brand tags or hangtags in view",
    "tag_readable": "Readable text on the tags",
    "product_visible": "The product itself, unfolded and in view",
    "product_turned": "The product turned over to show both sides",
    "label_with_barcode": "The label and its barcode in view together",
    "seal_visible": "The seal or tape in view",
    "tag_close_up": "A tag held close enough to read",
    "hand_on_product": "A hand handling the product",
}

CAP_TEXT = {
    "no_barcode_max_review": "If the barcode is never read, the video can't pass. It goes to a "
    "reviewer at best.",
    "low_quality_max_review": "If fewer than half the frames are usable (too dark or blurry), "
    "the video can't pass. It goes to a reviewer at best.",
    "too_short_fail": "A video shorter than 3 seconds always fails.",
}

TIPS = [
    "Record at 720p or better, in good light. Avoid backlight from windows.",
    "Keep the camera steady (a fixed mount is best) and the work area clear.",
    "Hold every label and tag close to the lens, in focus, for at least 2 seconds.",
    "Record one parcel per video, start to finish, without cutting or pausing.",
    "Keep your hands from covering the barcode while it is in view.",
]


def _threshold(check: Check) -> str:
    if check.key == "label_held":
        return f"at least {check.value} s"
    if check.key == "six_sides":
        return f"{check.value} sides"
    if check.key == "long_enough":
        return f"longer than {check.value} s"
    if check.key == "product_turned":
        return f"turned over at least {check.value} times"
    return ""


def _check_row(check: Check) -> str:
    what = WHAT_IT_LOOKS_FOR.get(check.key, check.key.replace("_", " ").capitalize())
    limit = _threshold(check)
    if limit:
        what = f"{what} ({limit})"
    partial = " Partial points available." if check.partial else ""
    fix = (check.fail_note or "").replace("|", "/")
    return f"| {what} | {check.points} | {fix}{partial} |"


def _rubric_section(rubric: Rubric) -> list[str]:
    d = rubric.decision
    lines = [
        f"## {rubric.title}",
        "",
        f"Rubric `{rubric.id}`. A video passes with **{d.pass_.min_score} or more points** "
        f"out of 100 when the system is confident; {d.review.min_score}–{d.pass_.min_score - 1} "
        f"points, or low confidence, sends it to a reviewer; below {d.review.min_score} fails.",
        "",
    ]
    for i, step in enumerate(rubric.steps, 1):
        lines += [
            f"### Step {i}. {step.title} ({step.weight} points)",
            "",
            f"**What to show:** {step.description}.",
            "",
            "| The system looks for | Points | If it's missed |",
            "|---|---|---|",
            *(_check_row(c) for c in step.checks),
            "",
        ]
    return lines


def render() -> str:
    rubrics = [get_rubric(rid) for rid in active_rubric_ids().values()]
    caps = {c.id for r in rubrics for c in r.caps}
    lines = [
        "# VMS recording SOP: what the system checks",
        "",
        "<!-- Generated from backend/vms/analysis/rubrics/*.yaml by "
        "`python -m vms.cli sop-doc --out docs/SOP.md`. Don't edit by hand. -->",
        "",
        "Every parcel you pack or unbox is filmed. That video is the evidence when a customer "
        "says an item was missing, wrong, damaged, or had its tags removed. The system watches "
        "each video and scores it out of 100 against the steps below.",
        "",
        "- **Pass:** every step was clearly shown. Nothing more to do.",
        "- **Review:** something was unclear. A reviewer watches the video and decides.",
        "- **Fail:** important steps were missing. The video may not protect you in a dispute.",
        "",
        "The system is cautious. When it is unsure, it asks a person instead of passing the "
        "video. A reviewer can overturn its decision, and every decision is recorded.",
        "",
        "## Rules that apply to every video",
        "",
        *(f"- {CAP_TEXT[c]}" for c in sorted(caps) if c in CAP_TEXT),
        "",
        "## How to film so it passes",
        "",
        *(f"- {t}" for t in TIPS),
        "",
    ]
    for rubric in rubrics:
        lines += _rubric_section(rubric)
    return "\n".join(lines).rstrip() + "\n"
