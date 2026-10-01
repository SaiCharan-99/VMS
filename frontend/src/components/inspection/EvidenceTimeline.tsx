import { formatDuration } from "@/lib/format";
import type { Status } from "@/types/analysis";

export interface TimelineMarker {
  id: number | string;
  t: number;
  step: number;
  status: Status;
  label: string;
}

const BG: Record<Status, string> = { pass: "bg-pass", review: "bg-review", fail: "bg-fail" };

export function EvidenceTimeline({
  markers,
  duration,
  current,
  onSeek,
}: {
  markers: TimelineMarker[];
  duration: number;
  current: number;
  onSeek: (t: number) => void;
}) {
  const pct = (t: number) => (duration > 0 ? Math.min(100, Math.max(0, (t / duration) * 100)) : 0);
  return (
    <div>
      <div className="relative mx-[11px] mt-3 h-[38px]">
        <div className="absolute inset-x-0 top-[17px] h-1 rounded-full bg-surface-2" />
        <div
          className="absolute left-0 top-[17px] h-1 rounded-full bg-accent"
          style={{ width: `${pct(current)}%` }}
        />
        {markers.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => onSeek(m.t)}
            title={`${m.label} · ${formatDuration(m.t)}`}
            aria-label={`Jump to ${formatDuration(m.t)}: step ${m.step}, ${m.label}`}
            className={`absolute top-2 -ml-[11px] grid h-[22px] w-[22px] place-items-center rounded-full border-2 border-surface text-[10px] font-bold text-on-status transition-transform hover:scale-110 ${BG[m.status]}`}
            style={{ left: `${pct(m.t)}%` }}
          >
            {m.step}
          </button>
        ))}
      </div>
      <div className="flex justify-between gap-2 text-[11.5px] text-text-3">
        <span>0:00</span>
        <span className="hidden text-center sm:inline">
          {markers.length ? "Click a marker to jump to the evidence" : "No evidence frames"}
        </span>
        <span>{formatDuration(duration)}</span>
      </div>
    </div>
  );
}
