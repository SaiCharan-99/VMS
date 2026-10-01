import { Card, CardHeader, StatusBadge } from "@/components/ui";
import { reasonLabel } from "@/lib/copy";
import { formatWhen } from "@/lib/format";
import type { Review } from "@/types/api";

/** Human decisions, newest first. The newest one sets the video's final status. */
export function ReviewHistory({ reviews }: { reviews: Review[] }) {
  if (reviews.length === 0) return null;
  const items = [...reviews].reverse();
  return (
    <Card>
      <CardHeader title="Review history" />
      <ol className="m-0 list-none p-0">
        {items.map((r, i) => (
          <li
            key={r.id}
            className="grid gap-1 border-t border-border px-[18px] py-3 first:border-t-0"
          >
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={r.final_status} human />
              <span className="font-medium">{reasonLabel(r.reason_code)}</span>
              {i === 0 && items.length > 1 && <span className="chip">Current</span>}
              <span className="ml-auto text-xs text-text-3">
                {r.reviewer_name ?? `User ${r.reviewer_id}`} · {formatWhen(r.created_at)}
              </span>
            </div>
            {r.comment && <p className="m-0 text-sm text-text-2">{r.comment}</p>}
          </li>
        ))}
      </ol>
    </Card>
  );
}
