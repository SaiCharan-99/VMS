import { forwardRef, useImperativeHandle, useRef, useState, type ReactNode } from "react";
import { apiUrl } from "@/api/client";
import { useRubrics } from "@/api/queries";
import { Bar, Button, Card, CardBody, CardHeader } from "@/components/ui";
import { checkText, isFullResult, STEP_TO_STATUS } from "@/lib/copy";
import { cn } from "@/lib/cn";
import { formatDuration, formatPct } from "@/lib/format";
import type { AnalysisResult, Status } from "@/types/analysis";
import type { VideoDetail } from "@/types/api";
import { EvidenceTimeline, type TimelineMarker } from "./EvidenceTimeline";
import { StepCard } from "./StepCard";
import { VerdictCard } from "./VerdictCard";
import { VideoPlayer, type VideoPlayerHandle } from "./VideoPlayer";

function PendingCard({
  detail,
  onReanalyze,
  busy,
}: {
  detail: VideoDetail;
  onReanalyze?: () => void;
  busy: boolean;
}) {
  const job = detail.job;
  if (job?.status === "failed") {
    return (
      <Card>
        <CardBody className="grid gap-2">
          <p className="m-0 font-semibold">Couldn&apos;t analyze this video</p>
          {job.error && <p className="m-0 text-sm text-text-2">{job.error}</p>}
          {onReanalyze && (
            <div>
              <Button onClick={onReanalyze} loading={busy}>
                Re-analyze
              </Button>
            </div>
          )}
        </CardBody>
      </Card>
    );
  }
  const p = job?.progress ?? 0;
  return (
    <Card>
      <CardBody className="grid gap-2.5" aria-live="polite">
        <p className="m-0 text-sm text-text-2">
          <span className="spin mr-2 align-[-1px]" aria-hidden />
          {job?.status === "queued" ? "Queued for analysis" : `Analyzing ${Math.round(p * 100)}%`}
        </p>
        <Bar value={p} label="Analysis progress" />
      </CardBody>
    </Card>
  );
}

function ResultFacts({ result }: { result: AnalysisResult }) {
  const q = result.quality;
  return (
    <Card>
      <CardHeader title="Barcodes & quality" />
      <CardBody className="grid gap-3 text-[13px]">
        <div>
          <div className="mb-1 text-text-3">Barcodes found</div>
          {result.barcodes.length ? (
            <ul className="m-0 grid list-none gap-1 p-0">
              {result.barcodes.map((b) => (
                <li key={b.value} className="flex flex-wrap gap-x-2">
                  <span className="mono font-medium">{b.value}</span>
                  <span className="text-text-2">
                    {b.symbology} · first at {formatDuration(b.first_seen_s)} · {b.frames_seen}{" "}
                    frames
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="m-0 text-text">None. Barcode not read; hold it steady in focus.</p>
          )}
        </div>
        <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4">
          {[
            ["Usable frames", formatPct(q.ok_ratio)],
            ["Blurry", String(q.frames_blurry)],
            ["Too dark", String(q.frames_dark)],
            ["Duration", formatDuration(result.video.duration_s)],
          ].map(([k, val]) => (
            <div key={k}>
              <dt className="text-text-3">{k}</dt>
              <dd className="tabular m-0 font-medium">{val}</dd>
            </div>
          ))}
        </dl>
        {result.caps_applied.length > 0 && (
          <p className="m-0 text-text-2">
            Held back from a pass by safety rules: {result.caps_applied.join(", ")}.
          </p>
        )}
      </CardBody>
    </Card>
  );
}

/** Player + evidence timeline, verdict, and step cards. Shared by the detail and review pages. */
export const InspectionView = forwardRef<
  VideoPlayerHandle,
  {
    detail: VideoDetail;
    /** Shown when the job failed; omit to hide Re-analyze. */
    onReanalyze?: () => void;
    reanalyzeBusy?: boolean;
    /** One column (the review page puts the queue beside it). */
    stacked?: boolean;
    /** Rendered after the step cards, e.g. review history. */
    after?: ReactNode;
  }
>(function InspectionView({ detail: d, onReanalyze, reanalyzeBusy = false, stacked, after }, ref) {
  const rubrics = useRubrics();
  const player = useRef<VideoPlayerHandle>(null);
  const [time, setTime] = useState({ t: 0, d: 0 });
  useImperativeHandle(
    ref,
    () => ({
      seek: (t: number) => player.current?.seek(t),
      skip: (dt: number) => player.current?.skip(dt),
    }),
    [],
  );

  const v = d.video;
  const analysis = d.analysis;
  const result = analysis && isFullResult<AnalysisResult>(analysis.result) ? analysis.result : null;
  const jobActive = d.job?.status === "queued" || d.job?.status === "running";
  const rubric = rubrics.data?.find((r) => r.id === result?.rubric_id);
  const status: Status | null = v.final_status === "pending" ? null : v.final_status;

  const seek = (t: number) => player.current?.seek(t);
  const stepIndex = new Map(result?.steps.map((s, i) => [s.key, i]) ?? []);
  const markers: TimelineMarker[] = (analysis?.evidence ?? []).flatMap((e) => {
    const i = stepIndex.get(e.step_key);
    const step = i === undefined ? undefined : result?.steps[i];
    if (!step || i === undefined) return [];
    const failed = step.checks.find((c) => !c.passed);
    return [
      {
        id: e.id,
        t: e.t_s,
        step: i + 1,
        status: STEP_TO_STATUS[step.status],
        label: `${step.title}${failed ? `: ${checkText(failed)}` : ""}`,
      },
    ];
  });
  const duration = time.d || result?.video.duration_s || v.duration_s || 0;

  return (
    <div
      className={cn(
        "grid items-start gap-5",
        !stacked && "lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]",
      )}
    >
      <div className={cn("min-w-0", !stacked && "lg:sticky lg:top-4")}>
        {v.stream_url ? (
          <>
            <VideoPlayer
              ref={player}
              key={v.id}
              src={apiUrl(v.stream_url)}
              label={v.original_filename}
              onTime={(t, dur) => setTime({ t, d: Number.isFinite(dur) ? dur : 0 })}
            />
            <EvidenceTimeline
              markers={markers}
              duration={duration}
              current={time.t}
              onSeek={seek}
            />
          </>
        ) : (
          <Card>
            <CardBody className="text-sm text-text-2">
              {v.file_purged
                ? "The video file was deleted by the retention policy. The analysis and evidence frames are kept."
                : "No video file for this record (imported from the old system)."}
            </CardBody>
          </Card>
        )}
      </div>

      <div className="grid min-w-0 gap-4">
        {!analysis || jobActive || d.job?.status === "failed" ? (
          <PendingCard
            detail={d}
            onReanalyze={v.stream_url ? onReanalyze : undefined}
            busy={reanalyzeBusy}
          />
        ) : null}
        {analysis && status && (
          <VerdictCard
            status={status}
            score={analysis.total_score}
            summary={result?.summary ?? analysis.decision}
            confidence={analysis.confidence}
            awb={v.awb}
            framesOk={result?.quality.frames_ok}
            framesSampled={result?.video.frames_sampled}
            human={d.reviews.length > 0}
          />
        )}
        {result ? (
          <>
            <Card>
              {result.steps.map((s, i) => (
                <StepCard
                  key={s.key}
                  index={i + 1}
                  step={s}
                  description={rubric?.steps.find((r) => r.key === s.key)?.description}
                  evidence={(analysis?.evidence ?? []).filter((e) => e.step_key === s.key)}
                  onSeek={seek}
                />
              ))}
            </Card>
            <ResultFacts result={result} />
          </>
        ) : (
          analysis && (
            <Card>
              <CardBody className="text-sm text-text-2">
                This is an older result format, so step details aren&apos;t available.
                {onReanalyze && v.stream_url && " Re-analyze to see them."}
              </CardBody>
            </Card>
          )
        )}
        {after}
      </div>
    </div>
  );
});
