import streamlit as st
import tempfile, os
import pandas as pd
from datetime import datetime
from vms.analysis import analyze_video
from vms.analysis.rubric import rubric_for
from vms.config import get_settings

st.set_page_config(page_title="VMS SOP Analyzer", page_icon="📦", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; color: #f0f0f0; }
.header-box {
    background: #1a1d27; padding: 16px 20px; border-radius: 8px;
    margin-bottom: 20px; border-left: 4px solid #3b82f6;
}
.verdict-accepted { background:#1a4731; color:#4ade80; padding:4px 14px; border-radius:5px; font-weight:700; font-size:13px; }
.verdict-review   { background:#3d2c00; color:#fbbf24; padding:4px 14px; border-radius:5px; font-weight:700; font-size:13px; }
.verdict-rejected { background:#3d0a0a; color:#f87171; padding:4px 14px; border-radius:5px; font-weight:700; font-size:13px; }
.big-score { font-size:38px; font-weight:700; }
.step-card {
    background:#12151f; border:0.5px solid #2a2d3a;
    border-radius:8px; padding:12px 14px; margin-bottom:8px;
}
.step-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
.step-title  { font-size:13px; font-weight:600; color:#e2e8f0; }
.step-pts    { font-size:13px; color:#475569; }
.step-pct    { font-size:12px; font-weight:600; }
.bar-bg  { background:#2a2d3a; border-radius:4px; height:7px; overflow:hidden; margin:4px 0 8px; }
.bar-fill{ height:7px; border-radius:4px; }
.step-note { font-size:12px; color:#f59e0b; }
.step-ok   { font-size:12px; color:#22c55e; }
.stat-box {
    background:#12151f; border:0.5px solid #2a2d3a;
    border-radius:8px; padding:10px 14px; text-align:center;
}
.stat-val { font-size:16px; font-weight:600; color:#e2e8f0; }
.stat-lbl { font-size:11px; color:#475569; margin-top:2px; }
.score-row { display:flex; align-items:center; gap:16px; margin-bottom:12px; }
.mode-badge-fwd { background:#1e3a5f; color:#60a5fa; padding:3px 10px; border-radius:4px; font-size:12px; font-weight:600; }
.mode-badge-ret { background:#2d1b4e; color:#a78bfa; padding:3px 10px; border-radius:4px; font-size:12px; font-weight:600; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h3 style="margin:0;color:#fff;font-weight:600;">📦 VMS SOP Analyzer</h3>
    <p style="margin:4px 0 0;color:#94a3b8;font-size:13px;">
        Inspection video scoring against VMS Logistics SOP
    </p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Configuration")
    process_type = st.selectbox("Process Mode", ["Return", "Forward"])

    rubric = rubric_for(process_type)
    checks = "\n".join(f"- {step.title}" for step in rubric.steps)
    st.info(f"**{rubric.title}**\n\nChecks:\n{checks}")

    uploaded_files = st.file_uploader(
        "Upload Inspection Videos",
        type=["mp4", "avi", "mov", "mkv"],
        accept_multiple_files=True
    )
    st.divider()
    blur_threshold = st.slider("Blur tolerance", 5.0, 100.0, 30.0, 5.0)
    st.divider()
    st.markdown("**💡 Slow upload?**")
    st.caption("• Phone: **Video Compress** app")
    st.caption("• PC: **HandBrake** — RF 28")
    st.caption("• Record at **720p** not 1080p")

def score_color(pct):
    if pct >= 85: return "#22c55e"
    if pct >= 50: return "#f59e0b"
    return "#ef4444"

def verdict_html(status):
    if status == "pass": return '<span class="verdict-accepted">✅ ACCEPTED</span>'
    if status == "review": return '<span class="verdict-review">⚠️ REVIEW REQUIRED</span>'
    return '<span class="verdict-rejected">❌ REJECTED</span>'


if not uploaded_files:
    st.info("Upload one or more inspection videos from the sidebar to begin.")
    st.stop()

mode_badge = (
    '<span class="mode-badge-fwd">📦 Forward — Packing</span>'
    if process_type == "Forward"
    else '<span class="mode-badge-ret">🔄 Return — Unboxing</span>'
)
st.markdown(
    f"**Batch Inspection — {len(uploaded_files)} video(s)** &nbsp; {mode_badge}",
    unsafe_allow_html=True
)

descriptions = {step.key: step.description for step in rubric.steps}
settings = get_settings().model_copy(update={"blur_threshold": blur_threshold})
all_rows = []

for uploaded in uploaded_files:
    st.divider()
    vid_col, analysis_col = st.columns([1, 1], gap="large")

    ext = os.path.splitext(uploaded.name)[1].lower() or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    with vid_col:
        st.markdown(f"**{uploaded.name}**")
        st.video(tmp_path)

    with analysis_col:
        with st.spinner(f"Analyzing {uploaded.name}..."):
            try:
                result = analyze_video(tmp_path, process_type, settings=settings)
            except Exception as e:
                os.remove(tmp_path)
                st.error(f"Could not analyze {uploaded.name}: {e}")
                continue

        os.remove(tmp_path)

        score   = result.total_score
        status  = result.status
        color   = score_color(score)
        metrics = result.metrics

        # ── Score + verdict ──
        st.markdown(
            f'<div class="score-row">'
            f'{verdict_html(status)}'
            f'<span class="big-score" style="color:{color}">{score}</span>'
            f'<span style="font-size:16px;color:#475569">/100 &nbsp;({score}%)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="bar-bg"><div class="bar-fill" '
            f'style="width:{score}%;background:{color}"></div></div>',
            unsafe_allow_html=True,
        )

        # ── Step cards ──
        for i, step in enumerate(result.steps, start=1):
            label    = f"{i}. {step.title}"
            earned   = step.score
            weight   = step.weight
            notes    = step.notes
            sop_desc = descriptions.get(step.key, "")
            spct     = round(earned / weight * 100)
            sc     = score_color(spct)

            notes_html = "".join(
                f'<div class="step-note">⚠ {n}</div>' for n in notes
            ) if notes else '<div class="step-ok">✓ No issues</div>'

            st.markdown(f"""
            <div class="step-card">
              <div class="step-header">
                <span class="step-title">{label}</span>
                <span>
                  <span class="step-pct" style="color:{sc}">{spct}%</span>
                  &nbsp;<span class="step-pts">{earned}/{weight} pts</span>
                </span>
              </div>
              <div class="bar-bg">
                <div class="bar-fill" style="width:{spct}%;background:{sc}"></div>
              </div>
              <div style="font-size:11px;color:#475569;margin-bottom:4px;font-style:italic">{sop_desc}</div>
              {notes_html}
            </div>
            """, unsafe_allow_html=True)

        # ── Stats ──
        sampled  = result.video.frames_sampled
        failures = sampled - result.quality.frames_ok
        sides    = metrics.get('estimated_sides', '?')

        # For forward, show "sides sealed" context differently
        sides_label = "Sides Sealed" if process_type == "Forward" else "Sides Shown"

        c1, c2, c3, c4 = st.columns(4)
        for col, val, lbl in [
            (c1, f"{result.video.duration_s:.1f}s", "Duration"),
            (c2, f"{sampled-failures}/{sampled}", "Frames OK"),
            (c3, f"{sides}/6",                   sides_label),
            (c4, process_type,                    "Mode"),
        ]:
            col.markdown(
                f'<div class="stat-box">'
                f'<div class="stat-val">{val}</div>'
                f'<div class="stat-lbl">{lbl}</div></div>',
                unsafe_allow_html=True,
            )

        follow_up_notes = " ".join(n.rstrip(".") for step in result.steps for n in step.notes)
        row = {
            "Timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M"),
            "File":            uploaded.name,
            "Process Type":    process_type,
            "Verdict":         result.decision,
            "Manual Summary":  result.summary,
            "Score %":         f"{score}%",
        }
        for step in result.steps:
            row[f"{step.title} %"] = f"{round(step.score / step.weight * 100)}%"
        row.update({
            "Barcodes":        ", ".join(b.value for b in result.barcodes) or "-",
            "Sides":           f"{sides}/6",
            "Duration (s)":    result.video.duration_s,
            "Follow-up Notes": follow_up_notes or "No follow-up points noted.",
        })
        all_rows.append(row)

if all_rows:
    st.divider()
    st.subheader("Batch Summary")
    df = pd.DataFrame(all_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download CSV Report",
        data=df.to_csv(index=False, encoding="utf-8-sig"),
        file_name=f"VMS_{process_type}_Audit_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
