import { useQueries, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/api/endpoints";
import { POLL_MS } from "@/api/queries";
import { useAuth } from "@/auth/AuthProvider";
import { hasRole, REVIEWER_UP } from "@/auth/roles";
import { FailedChecksList } from "@/components/charts/FailedChecksList";
import { Sparkline } from "@/components/charts/Sparkline";
import { StatusByDayChart } from "@/components/charts/StatusByDayChart";
import { VideoTable } from "@/components/VideoTable";
import { Card, CardBody, CardHeader, ErrorState, KpiTile, Skeleton } from "@/components/ui";
import { dayLabel, isoDate } from "@/lib/format";

const COUNTS = ["all", "pass", "review", "fail", "pending"] as const;

const show = (n: number | string | undefined) =>
  n === undefined ? (
    <Skeleton className="mt-1 h-7 w-16" />
  ) : typeof n === "number" ? (
    n.toLocaleString()
  ) : (
    n
  );
const pct = (r: number | null | undefined) =>
  r === null || r === undefined ? "—" : `${(r * 100).toFixed(1)}%`;

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return isoDate(d);
}

/** Operators can't call /reports, so their tiles come from page_size=1 list totals
 *  (the API already scopes them to their own uploads). */
function OperatorTiles() {
  const today = isoDate(new Date());
  const counts = useQueries({
    queries: COUNTS.map((s) => ({
      queryKey: ["videos", "count", s, today],
      queryFn: () =>
        api.videos({ status: s === "all" ? undefined : s, date_from: today, page_size: 1 }),
      refetchInterval: s === "pending" ? POLL_MS * 5 : undefined,
    })),
  });
  const [all, pass, review, fail, pending] = COUNTS.map((_, i) => counts[i]?.data?.total);
  const decided = (pass ?? 0) + (review ?? 0) + (fail ?? 0);
  return (
    <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiTile
          label="My inspections today"
          value={show(all)}
          delta={fail ? `${fail} rejected` : undefined}
          trend={fail ? "bad" : "neutral"}
        />
        <KpiTile
          label="Pass rate today"
          value={all === undefined ? show(undefined) : decided ? pct((pass ?? 0) / decided) : "—"}
          delta={decided ? `${pass} of ${decided} decided` : "No results yet"}
        />
        <KpiTile label="Sent for review today" value={show(review)} />
        <KpiTile label="Analyzing now" value={show(pending)} delta="uploaded today" />
      </div>
      {counts.some((c) => c.isError) && (
        <p role="alert" className="mt-2 text-sm text-fail">
          Some counts couldn&apos;t be loaded.
        </p>
      )}
    </>
  );
}

function ReviewerOverview() {
  const range = { date_from: daysAgo(6), date_to: isoDate(new Date()) };
  const summary = useQuery({
    queryKey: ["report", range, "day", "dashboard"],
    queryFn: () => api.reportSummary({ ...range, group_by: "day" }),
    refetchInterval: POLL_MS * 15,
  });
  const queue = useQuery({
    queryKey: ["review-queue", "count"],
    queryFn: () => api.reviewQueue({ page_size: 1 }),
  });
  const s = summary.data;
  const today = s?.groups[s.groups.length - 1];
  const yesterday = s?.groups[s.groups.length - 2];
  const trend =
    today?.pass_rate == null || yesterday?.pass_rate == null
      ? undefined
      : today.pass_rate - yesterday.pass_rate;

  if (summary.isError) {
    return (
      <Card>
        <ErrorState error={summary.error} onRetry={() => summary.refetch()} />
      </Card>
    );
  }
  return (
    <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiTile
          label="Inspected today"
          value={show(today?.total)}
          delta={today?.fail ? `${today.fail} rejected` : undefined}
          trend={today?.fail ? "bad" : "neutral"}
        />
        <KpiTile
          label="Pass rate today"
          value={show(today && pct(today.pass_rate))}
          delta={
            trend === undefined
              ? "7-day trend"
              : `${trend >= 0 ? "up" : "down"} ${Math.abs(trend * 100).toFixed(1)} pts vs yesterday`
          }
          trend={trend === undefined || trend === 0 ? "neutral" : trend > 0 ? "good" : "bad"}
        >
          {s && (
            <Sparkline
              label={`Pass rate, last 7 days: ${s.groups.map((g) => `${dayLabel(g.key)} ${pct(g.pass_rate)}`).join(", ")}`}
              points={s.groups.map((g) => ({
                label: dayLabel(g.key),
                value: g.pass_rate === null ? null : Math.round(g.pass_rate * 1000) / 10,
              }))}
            />
          )}
        </KpiTile>
        <KpiTile
          label="Awaiting review"
          value={show(queue.data?.total)}
          delta={queue.data?.total ? "Open the queue" : "Queue is clear"}
        />
        <KpiTile
          label="Model–reviewer agreement"
          value={show(s && pct(s.agreement_rate))}
          delta={s ? `7 days · ${s.agreement_n} pass/fail verdicts reviewed` : undefined}
        />
      </div>
      <div className="mt-4 grid items-start gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader title="Outcomes, last 7 days" />
          <CardBody>
            {s ? (
              <StatusByDayChart groups={s.groups} height={180} />
            ) : (
              <Skeleton className="h-[200px] w-full" />
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader
            title="Most-missed SOP checks"
            actions={
              <Link to="/reports" className="text-sm font-medium text-accent-text hover:underline">
                Reports
              </Link>
            }
          />
          <CardBody>
            {s ? (
              <FailedChecksList checks={s.top_failed_checks.slice(0, 5)} />
            ) : (
              <Skeleton className="h-[200px] w-full" />
            )}
          </CardBody>
        </Card>
      </div>
    </>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const recent = useQuery({
    queryKey: ["videos", { page_size: 5 }],
    queryFn: () => api.videos({ page_size: 5 }),
  });

  return (
    <>
      <h2 className="sr-only">Overview</h2>
      {hasRole(user, REVIEWER_UP) ? <ReviewerOverview /> : <OperatorTiles />}
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
