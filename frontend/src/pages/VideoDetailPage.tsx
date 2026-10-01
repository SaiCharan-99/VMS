import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiUrl } from "@/api/client";
import { api } from "@/api/endpoints";
import { useRubrics, useVideo } from "@/api/queries";
import { useAuth } from "@/auth/AuthProvider";
import { hasRole, REVIEWER_UP } from "@/auth/roles";
import { EvidenceTimeline, type TimelineMarker } from "@/components/inspection/EvidenceTimeline";
import { StepCard } from "@/components/inspection/StepCard";
import { VerdictCard } from "@/components/inspection/VerdictCard";
import { VideoPlayer, type VideoPlayerHandle } from "@/components/inspection/VideoPlayer";
import {
  Bar,
  Button,
  Card,
  CardBody,
  CardHeader,
  ErrorState,
  Skeleton,
  useToast,
} from "@/components/ui";
import { checkText, isFullResult, STEP_TO_STATUS } from "@/lib/copy";
import { formatDuration, formatPct } from "@/lib/format";
import type { AnalysisResult, Status } from "@/types/analysis";
import type { VideoDetail } from "@/types/api";

function DetailSkeleton() {
  return (
    <div aria-busy="true" className="grid gap-5 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
      <Skeleton className="aspect-video w-full" />
      <div className="grid gap-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  );
}

function PendingCard({
  detail,
  canReanalyze,
  onReanalyze,
  busy,
}: {
  detail: VideoDetail;
  canReanalyze: boolean;
  onReanalyze: () => void;
  busy: boolean;
}) {
  const job = detail.job;
  if (job?.status === "failed") {
    return (
      <Card>
        <CardBody className="grid gap-2">
          <p className="m-0 font-semibold">Couldn&apos;t analyze this video</p>
          {job.error && <p className="m-0 text-sm text-text-2">{job.error}</p>}
          {canReanalyze && (
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

export function VideoDetailPage() {
  const id = Number(useParams().id);
  const { user } = useAuth();
  const detail = useVideo(Number.isFinite(id) ? id : undefined);
  const rubrics = useRubrics();
  const player = useRef<VideoPlayerHandle>(null);
  const [time, setTime] = useState({ t: 0, d: 0 });
  const qc = useQueryClient();
  const toast = useToast();
  const canReanalyze = hasRole(user, REVIEWER_UP);

  const reanalyze = useMutation({
    mutationFn: () => api.reanalyze(id),
    onSuccess: () => {
      toast("Re-analysis queued.");
      void qc.invalidateQueries({ queryKey: ["video", id] });
    },
    onError: (err) => toast(err instanceof Error ? err.message : "Couldn't queue it.", "error"),
  });

  if (detail.isPending) return <DetailSkeleton />;
  if (detail.isError) {
    return (
      <Card>
        <ErrorState error={detail.error} onRetry={() => detail.refetch()} />
      </Card>
    );
  }

  const d = detail.data;
  const v = d.video;
  const analysis = d.analysis;
  const result = analysis && isFullResult<AnalysisResult>(analysis.result) ? analysis.result : null;
  const jobActive = d.job?.status === "queued" || d.job?.status === "running";
  const rubric = rubrics.data?.find((r) => r.id === result?.rubric_id);
  const human = d.reviews.length > 0;
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
    <>
      <div className="mb-4 flex flex-wrap items-center gap-2.5">
        <Link
          to="/videos"
          className="inline-flex items-center gap-1.5 rounded-ctl border border-border-strong bg-surface px-3.5 py-[7px] font-medium hover:bg-surface-2"
        >
          <ArrowLeft size={16} aria-hidden />
          Inspections
        </Link>
        <span className="mono min-w-0 truncate text-text-2">{v.original_filename}</span>
        <span className="chip">{v.process_type}</span>
        <span className="flex-1" />
        {canReanalyze && v.stream_url && (
          <Button
            onClick={() => reanalyze.mutate()}
            loading={reanalyze.isPending}
            disabled={jobActive}
          >
            <RefreshCw size={15} aria-hidden />
            Re-analyze
          </Button>
        )}
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <div className="min-w-0 lg:sticky lg:top-4">
          {v.stream_url ? (
            <>
              <VideoPlayer
                ref={player}
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
                No video file for this record (imported from the old system).
              </CardBody>
            </Card>
          )}
        </div>

        <div className="grid min-w-0 gap-4">
          {!analysis || jobActive || d.job?.status === "failed" ? (
            <PendingCard
              detail={d}
              canReanalyze={canReanalyze && Boolean(v.stream_url)}
              onReanalyze={() => reanalyze.mutate()}
              busy={reanalyze.isPending}
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
              human={human}
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
                  {canReanalyze && v.stream_url && " Re-analyze to see them."}
                </CardBody>
              </Card>
            )
          )}
        </div>
      </div>
    </>
  );
}
