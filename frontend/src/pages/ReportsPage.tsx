import { useMutation, useQuery } from "@tanstack/react-query";
import { BarChart3, Download } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/api/endpoints";
import { useStations } from "@/api/queries";
import { FailedChecksList } from "@/components/charts/FailedChecksList";
import { StatusByDayChart } from "@/components/charts/StatusByDayChart";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  DataTable,
  EmptyState,
  ErrorState,
  FilterBar,
  KpiTile,
  Segmented,
  Skeleton,
  useToast,
  type Column,
} from "@/components/ui";
import { dayLabel, isoDate } from "@/lib/format";
import type { ReportGroup } from "@/types/api";

type Preset = "7" | "30" | "90" | "custom";

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return isoDate(d);
}

const pct = (r: number | null | undefined) =>
  r === null || r === undefined ? "—" : `${(r * 100).toFixed(1)}%`;

function formatTurnaround(s: number | null): string {
  if (s === null) return "—";
  if (s < 3600) return `${Math.round(s / 60)} min`;
  if (s < 86400) return `${(s / 3600).toFixed(1)} h`;
  return `${(s / 86400).toFixed(1)} d`;
}

const GROUP_COLUMNS: Column<ReportGroup>[] = [
  { key: "label", header: "Name", cell: (g) => <span className="font-medium">{g.label}</span> },
  { key: "total", header: "Videos", numeric: true, cell: (g) => g.total },
  { key: "pass", header: "Pass", numeric: true, cell: (g) => g.pass },
  { key: "review", header: "Review", numeric: true, secondary: true, cell: (g) => g.review },
  { key: "fail", header: "Fail", numeric: true, cell: (g) => g.fail },
  { key: "rate", header: "Pass rate", numeric: true, cell: (g) => pct(g.pass_rate) },
  {
    key: "score",
    header: "Avg score",
    numeric: true,
    secondary: true,
    cell: (g) => (g.avg_score === null ? "—" : Math.round(g.avg_score)),
  },
];

const DAY_COLUMNS: Column<ReportGroup>[] = [
  { key: "day", header: "Day", cell: (g) => dayLabel(g.key) },
  ...GROUP_COLUMNS.slice(1),
];

export function ReportsPage() {
  const [params, setParams] = useSearchParams();
  const preset = (params.get("range") as Preset | null) ?? "7";
  const dateTo = params.get("to") ?? isoDate(new Date());
  const dateFrom = params.get("from") ?? daysAgo(Number(preset === "custom" ? 7 : preset) - 1);
  const processType = params.get("process_type") ?? "";
  const stationId = params.get("station_id") ?? "";
  const [breakdown, setBreakdown] = useState<"station" | "operator">("station");
  const stations = useStations();
  const toast = useToast();

  const base = {
    date_from: dateFrom,
    date_to: dateTo,
    process_type: processType || undefined,
    station_id: stationId || undefined,
  };
  const summary = useQuery({
    queryKey: ["report", base, "day"],
    queryFn: () => api.reportSummary({ ...base, group_by: "day" }),
  });
  const groups = useQuery({
    queryKey: ["report", base, breakdown],
    queryFn: () => api.reportSummary({ ...base, group_by: breakdown }),
  });
  const exportCsv = useMutation({
    mutationFn: () => api.exportCsv(base),
    onError: (err) => toast(err instanceof Error ? err.message : "Export failed.", "error"),
  });

  const update = (patch: Record<string, string>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    setParams(next, { replace: true });
  };
  const setPreset = (p: Preset) =>
    p === "custom"
      ? update({ range: "custom", from: dateFrom, to: dateTo })
      : update({ range: p, from: "", to: "" });

  const s = summary.data;
  const show = (v: string | number | undefined) =>
    v === undefined ? <Skeleton className="mt-1 h-7 w-16" /> : v;

  return (
    <>
      <FilterBar
        end={
          <Button onClick={() => exportCsv.mutate()} loading={exportCsv.isPending}>
            <Download size={15} aria-hidden />
            Export CSV
          </Button>
        }
      >
        <Segmented<Preset>
          label="Date range"
          value={preset}
          onChange={setPreset}
          options={[
            { value: "7", label: "7 days" },
            { value: "30", label: "30 days" },
            { value: "90", label: "90 days" },
            { value: "custom", label: "Custom" },
          ]}
        />
        {preset === "custom" && (
          <>
            <input
              type="date"
              className="input py-1.5"
              aria-label="From date"
              value={dateFrom}
              max={dateTo}
              onChange={(e) => update({ from: e.target.value })}
            />
            <input
              type="date"
              className="input py-1.5"
              aria-label="To date"
              value={dateTo}
              min={dateFrom}
              onChange={(e) => update({ to: e.target.value })}
            />
          </>
        )}
        <select
          className="select"
          aria-label="Process type"
          value={processType}
          onChange={(e) => update({ process_type: e.target.value })}
        >
          <option value="">All types</option>
          <option value="Forward">Forward</option>
          <option value="Return">Return</option>
        </select>
        <select
          className="select"
          aria-label="Station"
          value={stationId}
          onChange={(e) => update({ station_id: e.target.value })}
        >
          <option value="">All stations</option>
          {stations.data?.map((st) => (
            <option key={st.id} value={st.id}>
              {st.code} · {st.name}
            </option>
          ))}
        </select>
      </FilterBar>

      {summary.isError ? (
        <Card>
          <ErrorState error={summary.error} onRetry={() => summary.refetch()} />
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiTile
              label="Videos"
              value={show(s?.totals.total.toLocaleString())}
              delta={s ? `${s.analyzed} analyzed · ${s.totals.pending} analyzing` : undefined}
            />
            <KpiTile
              label="Pass rate (final)"
              value={show(s && pct(s.pass_rate))}
              delta={
                s ? `Avg score ${s.avg_score === null ? "—" : Math.round(s.avg_score)}` : undefined
              }
            />
            <KpiTile
              label="Review rate (model)"
              value={show(s && pct(s.review_rate))}
              delta={
                s
                  ? `${s.reviewed} reviewed · turnaround ${formatTurnaround(s.avg_turnaround_s)}`
                  : undefined
              }
            />
            <KpiTile
              label="Model–reviewer agreement"
              value={show(s && pct(s.agreement_rate))}
              delta={s ? `on ${s.agreement_n} pass/fail verdicts reviewed` : undefined}
            />
          </div>

          <div className="mt-4 grid items-start gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
            <Card>
              <CardHeader title="Outcome per day" />
              <CardBody>
                {!s ? (
                  <Skeleton className="h-[240px] w-full" />
                ) : s.totals.total === 0 ? (
                  <EmptyState icon={BarChart3} title="No inspections in this range." />
                ) : (
                  <>
                    <StatusByDayChart groups={s.groups} />
                    <details className="mt-3 text-sm">
                      <summary className="cursor-pointer text-text-2">View as table</summary>
                      <div className="mt-2 overflow-hidden rounded-ctl border border-border">
                        <DataTable
                          caption="Outcome per day"
                          columns={DAY_COLUMNS}
                          rows={s.groups}
                          rowKey={(g) => g.key}
                        />
                      </div>
                    </details>
                  </>
                )}
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Top failed checks" />
              <CardBody>
                {!s ? (
                  <Skeleton className="h-[240px] w-full" />
                ) : (
                  <FailedChecksList checks={s.top_failed_checks} />
                )}
              </CardBody>
            </Card>
          </div>

          <Card className="mt-4 overflow-hidden">
            <CardHeader
              title="Breakdown"
              actions={
                <Segmented
                  label="Break down by"
                  value={breakdown}
                  onChange={setBreakdown}
                  options={[
                    { value: "station", label: "Station" },
                    { value: "operator", label: "Operator" },
                  ]}
                />
              }
            />
            {groups.isError ? (
              <ErrorState error={groups.error} onRetry={() => groups.refetch()} />
            ) : (
              <DataTable
                caption={`Breakdown by ${breakdown}`}
                columns={GROUP_COLUMNS}
                rows={groups.data?.groups}
                rowKey={(g) => g.key || "none"}
                loading={groups.isPending}
                empty={<EmptyState icon={BarChart3} title="No inspections in this range." />}
              />
            )}
          </Card>
        </>
      )}
    </>
  );
}
