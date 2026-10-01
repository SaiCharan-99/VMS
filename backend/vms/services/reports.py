"""Compliance reports: KPIs, grouped counts, top failed checks, and the CSV export.

Aggregation happens in Python over one row per video, so the same code runs on SQLite and
Postgres without JSON-query dialects. Each video counts on the *local* day it was uploaded
(`tz_offset_min` = minutes east of UTC, e.g. 330 for IST).
"""

import csv
import io
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Literal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from vms.analysis.rubric import DEFAULT_RUBRICS, get_rubric
from vms.db.models import Analysis, FinalStatus, Review, Station, User, Video

GroupBy = Literal["day", "station", "operator", "process_type"]
STATUSES = ("pass", "review", "fail", "pending")


@dataclass
class VideoRow:
    """One video with the facts every report needs."""

    video: Video
    local_day: date
    analysis: Analysis | None
    review: Review | None
    reviewed_status: str | None  # model status of the analysis the latest review judged
    station: str | None
    operator: str | None
    reviewer: str | None


def utc_bounds(date_from: date, date_to: date, tz_offset_min: int) -> tuple[datetime, datetime]:
    """[start, end) in naive UTC for local dates `date_from..date_to` (inclusive)."""
    shift = timedelta(minutes=tz_offset_min)
    start = datetime.combine(date_from, time.min) - shift
    end = datetime.combine(date_to + timedelta(days=1), time.min) - shift
    return start, end


def load_rows(session: Session, stmt: Select, tz_offset_min: int = 0) -> list[VideoRow]:
    """`stmt` selects `Video`s; latest analysis/review and names are joined in a few queries."""
    videos = list(session.scalars(stmt))
    return list(_rows(session, videos, tz_offset_min))


def _rows(session: Session, videos: list[Video], tz_offset_min: int) -> Iterator[VideoRow]:
    ids = [v.id for v in videos]
    if not ids:
        return
    latest: dict[int, Analysis] = {}
    for a in session.scalars(
        select(Analysis).where(Analysis.video_id.in_(ids)).order_by(Analysis.id)
    ):
        latest[a.video_id] = a
    reviews: dict[int, Review] = {}
    for r in session.scalars(select(Review).where(Review.video_id.in_(ids)).order_by(Review.id)):
        reviews[r.video_id] = r
    reviewed_ids = {r.analysis_id for r in reviews.values()}
    reviewed_status = dict(
        session.execute(
            select(Analysis.id, Analysis.status).where(Analysis.id.in_(reviewed_ids))
        ).all()
    )
    user_ids = {v.uploaded_by for v in videos if v.uploaded_by} | {
        r.reviewer_id for r in reviews.values()
    }
    names = dict(session.execute(select(User.id, User.name).where(User.id.in_(user_ids))).all())
    station_ids = {v.station_id for v in videos if v.station_id}
    stations = dict(
        session.execute(select(Station.id, Station.code).where(Station.id.in_(station_ids))).all()
    )
    shift = timedelta(minutes=tz_offset_min)
    for v in videos:
        review = reviews.get(v.id)
        if v.uploaded_by:
            operator = names.get(v.uploaded_by)
        else:
            operator = "API key" if v.api_key_id else None
        yield VideoRow(
            video=v,
            local_day=(v.created_at + shift).date(),
            analysis=latest.get(v.id),
            review=review,
            reviewed_status=reviewed_status.get(review.analysis_id) if review else None,
            station=stations.get(v.station_id) if v.station_id else None,
            operator=operator,
            reviewer=names.get(review.reviewer_id) if review else None,
        )


# --- summary ---------------------------------------------------------------------------------


def _ratio(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


@dataclass
class _Bucket:
    counts: Counter = field(default_factory=Counter)
    scores: list[float] = field(default_factory=list)

    def add(self, row: VideoRow) -> None:
        self.counts[row.video.final_status.value] += 1
        if row.analysis is not None:
            self.scores.append(row.analysis.total_score)

    def out(self, key: str, label: str) -> dict[str, Any]:
        c = self.counts
        decided = c["pass"] + c["review"] + c["fail"]
        return {
            "key": key,
            "label": label,
            "total": sum(c.values()),
            **{s: c[s] for s in STATUSES},
            "pass_rate": _ratio(c["pass"], decided),
            "avg_score": _mean(self.scores),
        }


def _group_key(row: VideoRow, group_by: GroupBy) -> tuple[str, str]:
    if group_by == "day":
        return row.local_day.isoformat(), row.local_day.isoformat()
    if group_by == "station":
        return str(row.video.station_id or ""), row.station or "No station"
    if group_by == "operator":
        v = row.video
        key = (
            str(v.uploaded_by) if v.uploaded_by else (f"key:{v.api_key_id}" if v.api_key_id else "")
        )
        return key, row.operator or "Unknown"
    return row.video.process_type.value, row.video.process_type.value


def _failed_checks(rows: Iterable[VideoRow], limit: int) -> list[dict[str, Any]]:
    """Most frequent failed checks across the latest schema-2.0 analyses."""
    failures: Counter = Counter()
    evaluated: Counter = Counter()
    info: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        if row.analysis is None:
            continue
        result = row.analysis.result_json or {}
        steps = result.get("steps") if isinstance(result, dict) else None
        if not isinstance(steps, list):
            continue  # legacy 1.0 results have no per-check detail
        for step in steps:
            for check in step.get("checks") or []:
                k = (row.video.process_type.value, step.get("key", ""), check.get("key", ""))
                evaluated[k] += 1
                if not check.get("passed"):
                    failures[k] += 1
                    info.setdefault(k, {"step_title": step.get("title", k[1]), "note": None})
                    info[k]["note"] = info[k]["note"] or check.get("note")
    top = sorted(failures.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [
        {
            "process_type": k[0],
            "step_key": k[1],
            "check_key": k[2],
            "step_title": info[k]["step_title"],
            "note": info[k]["note"],
            "failures": n,
            "evaluated": evaluated[k],
            "rate": _ratio(n, evaluated[k]),
        }
        for k, n in top
    ]


def summarize(
    rows: list[VideoRow],
    date_from: date,
    date_to: date,
    group_by: GroupBy = "day",
    top_checks: int = 10,
) -> dict[str, Any]:
    """KPIs over `rows` (see IMPLEMENTATION.md §8 for the definitions).

    - pass_rate: final `pass` / videos with any analysis (final status not `pending`).
    - review_rate: latest model status `review` / analyzed videos.
    - agreement_rate: over reviewed videos whose judged analysis said pass or fail, the share
      where the human decision matched the model. Model `review` verdicts are excluded: the
      model abstained, so there is nothing to agree with.
    - avg_turnaround_s: upload → final decision (latest review, or the analysis for videos the
      model settled) over videos whose final status is pass/fail.
    """
    totals = _Bucket()
    groups: dict[str, tuple[str, _Bucket]] = {}
    model_review = reviewed = agree_n = agree = 0
    turnaround: list[float] = []
    for row in rows:
        totals.add(row)
        key, label = _group_key(row, group_by)
        groups.setdefault(key, (label, _Bucket()))[1].add(row)
        if row.analysis is not None and row.analysis.status == "review":
            model_review += 1
        if row.review is not None:
            reviewed += 1
            if row.reviewed_status in ("pass", "fail"):
                agree_n += 1
                agree += row.reviewed_status == row.review.final_status.value
        if row.video.final_status in (FinalStatus.pass_, FinalStatus.fail):
            decided_at = row.review.created_at if row.review else row.analysis.created_at
            turnaround.append((decided_at - row.video.created_at).total_seconds())

    if group_by == "day":  # every day in range, so charts have no gaps
        day = date_from
        while day <= date_to:
            groups.setdefault(day.isoformat(), (day.isoformat(), _Bucket()))
            day += timedelta(days=1)
    group_out = [b.out(k, label) for k, (label, b) in groups.items()]
    group_out.sort(key=lambda g: g["key"] if group_by == "day" else (-g["total"], g["label"]))

    t = totals.out("all", "All")
    analyzed = t["pass"] + t["review"] + t["fail"]
    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "group_by": group_by,
        "totals": {s: t[s] for s in ("total", *STATUSES)},
        "analyzed": analyzed,
        "pass_rate": t["pass_rate"],
        "review_rate": _ratio(model_review, analyzed),
        "reviewed": reviewed,
        "agreement_rate": _ratio(agree, agree_n),
        "agreement_n": agree_n,
        "avg_score": t["avg_score"],
        "avg_turnaround_s": _mean(turnaround),
        "top_failed_checks": _failed_checks(rows, top_checks),
        "groups": group_out,
    }


# --- CSV -------------------------------------------------------------------------------------


def step_titles() -> list[str]:
    """Union of active rubric step titles, in rubric order (Forward first)."""
    titles: list[str] = []
    for rubric_id in DEFAULT_RUBRICS.values():
        for step in get_rubric(rubric_id).steps:
            if step.title not in titles:
                titles.append(step.title)
    return titles


def csv_header(titles: list[str]) -> list[str]:
    return [
        "Timestamp",
        "File",
        "Process Type",
        "Verdict",
        "Manual Summary",
        "Score %",
        *[f"{t} %" for t in titles],
        "Sides",
        "Duration (s)",
        "Follow-up Notes",
        "AWB",
        "Station",
        "Operator",
        "Final Status",
        "Reviewer",
        "Review Reason",
        "Review Comment",
    ]


def csv_row(row: VideoRow, titles: list[str], tz_offset_min: int = 0) -> list[Any]:
    v, a, r = row.video, row.analysis, row.review
    result: dict[str, Any] = (a.result_json or {}) if a else {}
    steps = result.get("steps") if isinstance(result.get("steps"), list) else []
    pct = {
        s.get("title"): f"{round(s.get('score', 0) / s['weight'] * 100)}%"
        for s in steps
        if s.get("weight")
    }
    notes = " ".join(n.rstrip(".") for s in steps for n in s.get("notes") or [])
    sides = (result.get("metrics") or {}).get("estimated_sides")
    local = v.created_at + timedelta(minutes=tz_offset_min)
    return [
        local.strftime("%Y-%m-%d %H:%M"),
        v.original_filename,
        v.process_type.value,
        a.decision if a else "",
        result.get("summary", ""),
        f"{a.total_score}%" if a else "",
        *[pct.get(t, "") for t in titles],
        f"{sides}/6" if sides is not None else "",
        v.duration_s if v.duration_s is not None else "",
        notes if a else "",
        v.awb or "",
        row.station or "",
        row.operator or "",
        v.final_status.value,
        row.reviewer or "",
        r.reason_code if r else "",
        (r.comment or "") if r else "",
    ]


def stream_csv(
    session: Session, stmt: Select, tz_offset_min: int = 0, batch: int = 500
) -> Iterator[str]:
    """UTF-8 CSV with a BOM (so Excel detects the encoding), `batch` videos per query."""
    titles = step_titles()
    buf = io.StringIO()
    writer = csv.writer(buf)

    def flush() -> str:
        out = buf.getvalue()
        buf.seek(0)
        buf.truncate()
        return out

    writer.writerow(csv_header(titles))
    yield "﻿" + flush()
    offset = 0
    while True:
        videos = list(session.scalars(stmt.offset(offset).limit(batch)))
        if not videos:
            break
        for row in _rows(session, videos, tz_offset_min):
            writer.writerow(csv_row(row, titles, tz_offset_min))
        yield flush()
        offset += batch
        session.expunge_all()
