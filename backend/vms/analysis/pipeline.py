"""sampling → detectors → metrics → rubric → decision + caps → evidence → AnalysisResult."""

import time
from collections.abc import Callable
from pathlib import Path

from vms import __version__
from vms.analysis import confidence as confidence_mod
from vms.analysis import metrics as metrics_mod
from vms.analysis import rubric as rubric_mod
from vms.analysis import summary as summary_mod
from vms.analysis.detectors.barcode import BarcodeDetector
from vms.analysis.detectors.base import Detector, FrameSignals
from vms.analysis.detectors.motion import MotionDetector
from vms.analysis.detectors.objects import ObjectsDetector
from vms.analysis.detectors.ocr import OcrDetector
from vms.analysis.detectors.quality import QualityDetector
from vms.analysis.evidence import EvidenceSelector
from vms.analysis.result import AnalysisResult, Barcode, EngineInfo, QualitySummary, VideoInfo
from vms.analysis.sampling import Frame, VideoSampler
from vms.config import Settings, get_settings

ProgressCallback = Callable[[float], None]


def _ms(seconds: float) -> int:
    return round(seconds * 1000)


def _run(det: Detector, frame: Frame, sig: FrameSignals, timings: dict[str, float]) -> None:
    t0 = time.perf_counter()
    det.process(frame, sig)
    timings[det.name] += time.perf_counter() - t0


def _barcodes(signals: list[FrameSignals]) -> list[Barcode]:
    found: dict[str, Barcode] = {}
    for s in signals:
        for hit in s.barcodes:
            if hit.value in found:
                found[hit.value].frames_seen += 1
            else:
                found[hit.value] = Barcode(
                    value=hit.value,
                    symbology=hit.symbology,
                    first_seen_s=round(s.t_s, 2),
                    frames_seen=1,
                )
    return list(found.values())


def _quality(signals: list[FrameSignals], qd: QualityDetector) -> QualitySummary:
    n = len(signals)
    ok = sum(s.valid for s in signals)
    dark = sum(qd.is_dark(s) for s in signals)
    return QualitySummary(
        frames_ok=ok,
        frames_dark=dark,
        frames_blurry=sum(qd.is_blurry(s) and not qd.is_dark(s) for s in signals),
        avg_blur=round(sum(s.blur for s in signals) / n, 2) if n else 0.0,
        avg_brightness=round(sum(s.brightness for s in signals) / n, 2) if n else 0.0,
        ok_ratio=round(ok / n, 4) if n else 0.0,
    )


def analyze_video(
    path: str | Path,
    process_type: str,
    *,
    settings: Settings | None = None,
    evidence_dir: Path | None = None,
    progress_cb: ProgressCallback | None = None,
) -> AnalysisResult:
    """Analyze one video. `progress_cb` receives 0..1 while frames are processed."""
    t_start = time.perf_counter()
    settings = settings or get_settings()
    rubric = rubric_mod.rubric_for(process_type)

    sampler = VideoSampler(Path(path), settings.process_fps, settings.analysis_width)
    meta = sampler.meta
    quality = QualityDetector(
        settings.blur_threshold, settings.min_brightness, settings.max_brightness
    )
    objects, barcode, ocr = (
        ObjectsDetector(settings),
        BarcodeDetector(),
        OcrDetector(settings.ocr_every_n, settings.ocr_width),
    )
    every_frame: list[Detector] = [quality, MotionDetector()]
    valid_only: list[Detector] = [objects, barcode, ocr]  # order matters: OCR reads `label`
    selector = EvidenceSelector(rubric)

    timings = {d.name: 0.0 for d in every_frame + valid_only}
    signals: list[FrameSignals] = []
    t_sampling = 0.0
    frames = iter(sampler)
    while True:
        t0 = time.perf_counter()
        frame = next(frames, None)
        t_sampling += time.perf_counter() - t0
        if frame is None:
            break
        sig = FrameSignals(t_s=frame.t_s)
        for det in every_frame:
            _run(det, frame, sig, timings)
        if sig.valid:  # set by the quality detector above
            for det in valid_only:
                _run(det, frame, sig, timings)
        selector.offer(frame.bgr, sig)
        signals.append(sig)
        if progress_cb and meta.frames_total:
            progress_cb(min(1.0, (frame.idx + 1) / meta.frames_total))

    t0 = time.perf_counter()
    # Frame counts in container headers can be wrong; trust what we actually decoded if larger.
    duration_s = max(meta.duration_s, signals[-1].t_s if signals else 0.0)
    metrics = metrics_mod.aggregate(signals, duration_s, meta.sample_interval_s)
    steps = rubric_mod.evaluate(rubric, metrics)
    total = sum(s.score for s in steps)
    conf = confidence_mod.compute(metrics)
    status, decision, caps = rubric_mod.decide(rubric, total, conf, metrics)
    t_scoring = time.perf_counter() - t0

    t0 = time.perf_counter()
    evidence = selector.save(evidence_dir, settings.data_dir)
    for step in steps:
        step.evidence = evidence.get(step.key, [])
    t_evidence = time.perf_counter() - t0

    barcodes = _barcodes(signals)
    timings_ms = {
        "sampling": _ms(t_sampling),
        "detectors": _ms(sum(timings.values())),
        **{f"det_{name}": _ms(t) for name, t in timings.items()},
        "scoring": _ms(t_scoring),
        "evidence": _ms(t_evidence),
    }
    timings_ms["total"] = _ms(time.perf_counter() - t_start)
    if progress_cb:
        progress_cb(1.0)

    return AnalysisResult(
        process_type=rubric.process_type,
        rubric_id=rubric.id,
        engine=EngineInfo(
            version=__version__,
            detectors={
                "ocr": ocr.available,
                "barcode": barcode.available,
                "objects": objects.backend,
                "motion": True,
            },
        ),
        video=VideoInfo(
            duration_s=round(duration_s, 2),
            fps=round(meta.fps, 3),
            frames_total=meta.frames_total,
            frames_sampled=len(signals),
            width=meta.width,
            height=meta.height,
        ),
        quality=_quality(signals, quality),
        barcodes=barcodes,
        metrics=metrics,
        steps=steps,
        total_score=total,
        confidence=conf,
        status=status,
        decision=decision,
        caps_applied=caps,
        summary=summary_mod.render(rubric.process_type, decision, steps, bool(barcodes), conf),
        timings_ms=timings_ms,
    )
