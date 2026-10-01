import { useQueries, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/api/endpoints";
import { POLL_MS } from "@/api/queries";
import { useAuth } from "@/auth/AuthProvider";
import { VideoTable } from "@/components/VideoTable";
import { Card, CardHeader, ErrorState, KpiTile, Skeleton } from "@/components/ui";
import { isoDate } from "@/lib/format";

const COUNTS = ["all", "pass", "review", "fail", "pending"] as const;

export function DashboardPage() {
  const { user } = useAuth();
  const today = isoDate(new Date());
  // Totals come from page_size=1 list calls; the API already scopes operators to their own uploads.
  const counts = useQueries({
    queries: COUNTS.map((s) => ({
      queryKey: ["videos", "count", s, today],
      queryFn: () =>
        api.videos({
          status: s === "all" ? undefined : s,
          date_from: today,
          page_size: 1,
        }),
      refetchInterval: s === "pending" ? POLL_MS * 5 : undefined,
    })),
  });
  const reviewQueue = useQuery({
    queryKey: ["videos", "count", "review", "all-time"],
    queryFn: () => api.videos({ status: "review", page_size: 1 }),
  });
  const recent = useQuery({
    queryKey: ["videos", { page_size: 5 }],
    queryFn: () => api.videos({ page_size: 5 }),
  });

  const total = (i: number) => counts[i]?.data?.total;
  const [all, pass, review, fail, pending] = COUNTS.map((_, i) => total(i));
  const decided = (pass ?? 0) + (review ?? 0) + (fail ?? 0);
  const passRate = decided ? `${((100 * (pass ?? 0)) / decided).toFixed(1)}%` : "—";
  const show = (n: number | undefined) =>
    n === undefined ? <Skeleton className="mt-1 h-7 w-16" /> : n.toLocaleString();
  const mine = user?.role === "operator";

  return (
    <>
      <h2 className="sr-only">Today</h2>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiTile
          label={mine ? "My inspections today" : "Inspected today"}
          value={show(all)}
          delta={fail ? `${fail} rejected` : undefined}
          trend={fail ? "bad" : "neutral"}
        />
        <KpiTile
          label="Pass rate today"
          value={all === undefined ? show(undefined) : passRate}
          delta={decided ? `${pass} of ${decided} decided` : "No results yet"}
        />
        <KpiTile label="Awaiting review" value={show(reviewQueue.data?.total)} delta="all time" />
        <KpiTile label="Analyzing now" value={show(pending)} delta="uploaded today" />
      </div>
      {counts.some((c) => c.isError) && (
        <p role="alert" className="mt-2 text-sm text-fail">
          Some counts couldn&apos;t be loaded.
        </p>
      )}
      <Card className="mt-4 overflow-hidden">
        <CardHeader
          title="Recent inspections"
          actions={
            <Link
              to="/videos"
              className="rounded-ctl border border-border-strong bg-surface px-3.5 py-[7px] font-medium hover:bg-surface-2"
            >
              View all
            </Link>
          }
        />
        {recent.isError ? (
          <ErrorState error={recent.error} onRetry={() => recent.refetch()} />
        ) : (
          <VideoTable rows={recent.data?.items} loading={recent.isPending} />
        )}
      </Card>
    </>
  );
}
