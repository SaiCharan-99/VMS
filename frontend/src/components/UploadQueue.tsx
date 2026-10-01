import { X } from "lucide-react";
import { Link } from "react-router-dom";
import { useJob, useVideo } from "@/api/queries";
import { Bar, StatusBadge } from "@/components/ui";
import { formatBytes } from "@/lib/format";
import type { UploadItem } from "@/upload/queue";

function RowState({ item }: { item: UploadItem }) {
  const job = useJob(item.phase === "uploaded" ? item.jobId : undefined);
  const jobDone = item.phase === "uploaded" && (!item.jobId || job.data?.status === "done");
  const video = useVideo(jobDone ? item.videoId : undefined);

  let bar = <Bar value={0} tone="muted" label="Waiting" />;
  let state: React.ReactNode = <span className="text-sm text-text-2">Waiting…</span>;

  if (item.phase === "uploading") {
    bar = <Bar value={item.progress} tone="muted" label="Upload progress" />;
    state = (
      <span className="text-sm text-text-2">Uploading {Math.round(item.progress * 100)}%</span>
    );
  } else if (item.phase === "error") {
    bar = <Bar value={1} tone="fail" label="Upload failed" />;
    state = <span className="text-sm text-fail">{item.error}</span>;
  } else if (item.phase === "uploaded") {
    const j = job.data;
    const v = video.data;
    if (j?.status === "failed") {
      bar = <Bar value={1} tone="fail" label="Analysis failed" />;
      state = <span className="text-sm text-fail">Couldn&apos;t analyze this video</span>;
    } else if (v && v.video.final_status !== "pending") {
      const s = v.video.final_status;
      bar = <Bar value={1} tone={s} label="Done" />;
      const score = v.video.latest_analysis?.total_score;
      state = (
        <Link
          to={`/videos/${item.videoId}`}
          className="rounded-full"
          aria-label={`Open inspection for ${item.file.name}`}
        >
          <StatusBadge
            status={s}
            human={v.reviews.length > 0}
            suffix={score !== undefined ? String(score) : undefined}
          />
        </Link>
      );
    } else {
      const p = j?.progress ?? 0;
      bar = <Bar value={p} tone="accent" label="Analysis progress" />;
      state = (
        <span className="text-sm text-text-2">
          <span className="spin mr-2 align-[-1px]" aria-hidden />
          {j?.status === "queued" ? "Queued for analysis" : `Analyzing ${Math.round(p * 100)}%`}
        </span>
      );
    }
  }

  return (
    <>
      <div>{bar}</div>
      <div aria-live="polite">{state}</div>
    </>
  );
}

export function UploadQueue({
  items,
  onRemove,
}: {
  items: UploadItem[];
  onRemove: (id: string) => void;
}) {
  return (
    <ul className="m-0 list-none p-0">
      {items.map((item, i) => (
        <li
          key={item.id}
          className={`grid grid-cols-1 items-center gap-2 px-[18px] py-3 md:grid-cols-[minmax(0,1fr)_160px_minmax(140px,auto)_auto] md:gap-4 ${i ? "border-t border-border" : ""}`}
        >
          <div className="min-w-0">
            <div className="truncate font-medium">
              {item.videoId && item.phase === "uploaded" ? (
                <Link to={`/videos/${item.videoId}`} className="hover:underline">
                  {item.file.name}
                </Link>
              ) : (
                item.file.name
              )}
            </div>
            <div className="text-xs text-text-3">
              {formatBytes(item.file.size)} · {item.settings.process_type}
              {item.duplicate && " · already uploaded"}
            </div>
          </div>
          <RowState item={item} />
          <div className="hidden md:block">
            {(item.phase === "queued" || item.phase === "error") && (
              <button
                type="button"
                onClick={() => onRemove(item.id)}
                aria-label={`Remove ${item.file.name}`}
                className="rounded text-text-2 hover:text-text"
              >
                <X size={16} aria-hidden />
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
