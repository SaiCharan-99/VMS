import { checkLabel } from "@/lib/copy";
import type { FailedCheck } from "@/types/api";

/** Horizontal bars (accent, one series) for the most-failed checks, with counts as text. */
export function FailedChecksList({ checks }: { checks: FailedCheck[] }) {
  if (checks.length === 0) {
    return <p className="m-0 text-sm text-text-2">No failed checks in this range.</p>;
  }
  const max = Math.max(...checks.map((c) => c.failures));
  return (
    <ol className="m-0 grid list-none gap-2.5 p-0" aria-label="Most-failed SOP checks">
      {checks.map((c) => {
        const rate = c.rate === null ? "" : `, ${Math.round(c.rate * 100)}% of ${c.evaluated}`;
        return (
          <li
            key={`${c.process_type}-${c.step_key}-${c.check_key}`}
            className="grid grid-cols-[minmax(0,1.4fr)_minmax(60px,1fr)_auto] items-center gap-2.5 text-[13px]"
            title={c.note ?? undefined}
          >
            <span className="min-w-0">
              <span className="block truncate">{checkLabel(c.check_key)}</span>
              <span className="block truncate text-xs text-text-3">
                {c.process_type} · {c.step_title}
              </span>
            </span>
            <span className="h-2 overflow-hidden rounded-full bg-surface-2" aria-hidden>
              <span
                className="block h-full rounded-full bg-accent"
                style={{ width: `${(100 * c.failures) / max}%` }}
              />
            </span>
            <span className="tabular text-right text-text-2">
              {c.failures}
              <span className="sr-only"> failures{rate}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
