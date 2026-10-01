import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "@/api/endpoints";
import { useStations, useVideo } from "@/api/queries";
import { InspectionView } from "@/components/inspection/InspectionView";
import type { VideoPlayerHandle } from "@/components/inspection/VideoPlayer";
import { ReviewBar } from "@/components/review/ReviewBar";
import { commentRequired, type ReviewDraft } from "@/lib/review";
import { ReviewHistory } from "@/components/review/ReviewHistory";
import {
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  FilterBar,
  Kbd,
  Skeleton,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { REASON_LABEL } from "@/lib/copy";
import { formatWhen } from "@/lib/format";
import { REASON_CODES, type Page, type Video } from "@/types/api";

const EMPTY: ReviewDraft = { reason: "", comment: "" };
const SKIP_S = 5;

function isField(el: EventTarget | null): boolean {
  return el instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName);
}

export function ReviewPage() {
  const [params, setParams] = useSearchParams();
  const filters = {
    process_type: params.get("process_type") ?? undefined,
    station_id: params.get("station_id") ?? undefined,
  };
  const queueKey = ["review-queue", filters];
  const qc = useQueryClient();
  const toast = useToast();
  const stations = useStations();
  const queue = useQuery({
    queryKey: queueKey,
    queryFn: () => api.reviewQueue({ ...filters, page_size: 100 }),
  });
  const items = queue.data?.items ?? [];

  const [selected, setSelected] = useState<number | undefined>();
  const current = items.find((v) => v.id === selected) ?? items[0];
  const detail = useVideo(current?.id);
  const [draft, setDraft] = useState<ReviewDraft>(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const player = useRef<VideoPlayerHandle>(null);
  const reasonRef = useRef<HTMLSelectElement>(null);

  const select = (id: number | undefined) => {
    setSelected(id);
    setDraft(EMPTY);
    setError(null);
  };
  const nextAfter = (id: number): number | undefined => {
    const i = items.findIndex((v) => v.id === id);
    const rest = items.filter((v) => v.id !== id);
    return rest.length ? rest[Math.min(i, rest.length - 1)]?.id : undefined;
  };

  const review = useMutation({
    mutationFn: (vars: { video: Video; decision: "pass" | "fail"; draft: ReviewDraft }) =>
      api.review(vars.video.id, {
        final_status: vars.decision,
        reason_code: vars.draft.reason as (typeof REASON_CODES)[number],
        comment: vars.draft.comment.trim() || undefined,
      }),
    // Optimistic: drop the item and move on at once; restore it if the API refuses.
    onMutate: async ({ video }) => {
      await qc.cancelQueries({ queryKey: queueKey });
      const prev = qc.getQueryData<Page<Video>>(queueKey);
      if (prev) {
        qc.setQueryData<Page<Video>>(queueKey, {
          ...prev,
          items: prev.items.filter((v) => v.id !== video.id),
          total: prev.total - 1,
        });
      }
      select(nextAfter(video.id));
      return { prev };
    },
    onSuccess: (_r, { video, decision }) => {
      toast(`${video.original_filename}: marked ${decision === "pass" ? "Pass" : "Fail"}.`);
      void qc.invalidateQueries({ queryKey: ["video", video.id] });
      void qc.invalidateQueries({ queryKey: ["videos"] });
    },
    onError: (err, { video, draft: sent }, ctx) => {
      if (ctx?.prev) qc.setQueryData(queueKey, ctx.prev);
      setSelected(video.id);
      setDraft(sent);
      setError(err instanceof Error ? err.message : "Couldn't save the review.");
    },
    onSettled: () => void qc.invalidateQueries({ queryKey: ["review-queue"] }),
  });

  const decide = (decision: "pass" | "fail") => {
    if (!current || review.isPending) return;
    if (!draft.reason) {
      setError("Choose a reason first (keys 1–7).");
      reasonRef.current?.focus();
      return;
    }
    if (!draft.comment.trim() && commentRequired(draft, decision, detail.data?.analysis?.status)) {
      setError(
        draft.reason === "other"
          ? "Add a comment for reason Other."
          : "Add a comment: this overturns the model's verdict.",
      );
      return;
    }
    review.mutate({ video: current, decision, draft });
  };

  // Page-level shortcuts; ignored while typing in a field (Esc leaves the field).
  const keys = useRef({ decide, current, items });
  keys.current = { decide, current, items };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isField(e.target)) {
        (e.target as HTMLElement).blur();
        return;
      }
      if (isField(e.target) || e.ctrlKey || e.metaKey || e.altKey) return;
      const { decide: go, current: cur, items: list } = keys.current;
      const k = e.key.toLowerCase();
      if (k === "p" || k === "f") {
        e.preventDefault();
        go(k === "p" ? "pass" : "fail");
      } else if (k === "n" && cur && list.length > 1) {
        const i = list.findIndex((v) => v.id === cur.id);
        select(list[(i + 1) % list.length]?.id);
      } else if (k === "j" || k === "k") {
        player.current?.skip(k === "j" ? -SKIP_S : SKIP_S);
      } else if (/^[1-7]$/.test(e.key)) {
        const reason = REASON_CODES[Number(e.key) - 1];
        if (reason) {
          setDraft((d) => ({ ...d, reason }));
          setError(null);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
    select(undefined);
  };

  return (
    <>
      <FilterBar>
        <select
          className="select"
          aria-label="Process type"
          value={filters.process_type ?? ""}
          onChange={(e) => setFilter("process_type", e.target.value)}
        >
          <option value="">All types</option>
          <option value="Forward">Forward</option>
          <option value="Return">Return</option>
        </select>
        <select
          className="select"
          aria-label="Station"
          value={filters.station_id ?? ""}
          onChange={(e) => setFilter("station_id", e.target.value)}
        >
          <option value="">All stations</option>
          {stations.data?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.code} · {s.name}
            </option>
          ))}
        </select>
      </FilterBar>

      <div className="grid items-start gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
        <Card className="overflow-hidden">
          <CardHeader title={`Queue · ${queue.data?.total ?? "…"}`} />
          {queue.isError ? (
            <ErrorState error={queue.error} onRetry={() => queue.refetch()} />
          ) : queue.isPending ? (
            <div className="grid gap-2 p-4" aria-busy="true">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-11 w-full" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              icon={CheckCheck}
              title="The queue is clear. Nothing needs review."
              action={
                <Link to="/videos" className="font-medium text-accent-text hover:underline">
                  Browse inspections
                </Link>
              }
            />
          ) : (
            <ul
              aria-label="Videos awaiting review, oldest first"
              className="m-0 max-h-[40vh] list-none overflow-y-auto p-0 lg:max-h-[calc(100vh-200px)]"
            >
              {items.map((v) => {
                const on = v.id === current?.id;
                return (
                  <li key={v.id}>
                    <button
                      type="button"
                      aria-current={on || undefined}
                      onClick={() => select(v.id)}
                      className={cn(
                        "grid w-full gap-1 border-b border-border px-4 py-3 text-left focus-visible:-outline-offset-2",
                        on
                          ? "bg-accent-soft shadow-[inset_3px_0_0_var(--accent)]"
                          : "hover:bg-surface-2",
                      )}
                    >
                      <span className="truncate font-medium">{v.original_filename}</span>
                      <span className="flex items-center gap-2 text-xs text-text-2">
                        <StatusBadge
                          status="review"
                          suffix={String(v.latest_analysis?.total_score ?? "—")}
                        />
                        <span className="chip">{v.process_type}</span>
                        <span className="ml-auto whitespace-nowrap">
                          {formatWhen(v.created_at)}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <div className="min-w-0">
          {current &&
            (detail.isError ? (
              <Card>
                <ErrorState error={detail.error} onRetry={() => detail.refetch()} />
              </Card>
            ) : !detail.data || detail.data.video.id !== current.id ? (
              <div className="grid gap-4" aria-busy="true">
                <Skeleton className="aspect-video w-full" />
                <Skeleton className="h-32 w-full" />
              </div>
            ) : (
              <>
                <div className="mb-3 flex flex-wrap items-center gap-2.5">
                  <Link
                    to={`/videos/${current.id}`}
                    className="mono min-w-0 truncate font-medium text-accent-text hover:underline"
                  >
                    {current.original_filename}
                  </Link>
                  {current.awb && <span className="mono text-text-2">{current.awb}</span>}
                </div>
                <InspectionView
                  ref={player}
                  detail={detail.data}
                  stacked
                  after={<ReviewHistory reviews={detail.data.reviews} />}
                />
                <ReviewBar
                  ref={reasonRef}
                  draft={draft}
                  onChange={(d) => {
                    setDraft(d);
                    setError(null);
                  }}
                  onDecide={decide}
                  busy={review.isPending}
                  error={error}
                />
              </>
            ))}
          <p className="mt-2 text-xs text-text-3">
            Shortcuts: <Kbd>1</Kbd>–<Kbd>7</Kbd> reason · <Kbd>P</Kbd> pass · <Kbd>F</Kbd> fail ·{" "}
            <Kbd>N</Kbd> next · <Kbd>J</Kbd>/<Kbd>K</Kbd> seek ±5 s · <Kbd>Esc</Kbd> leave a field
          </p>
          <details className="mt-1 text-xs text-text-3">
            <summary className="cursor-pointer">Reason keys</summary>
            <ol className="m-0 mt-1 pl-5">
              {REASON_CODES.map((c) => (
                <li key={c}>{REASON_LABEL[c]}</li>
              ))}
            </ol>
          </details>
        </div>
      </div>
    </>
  );
}
