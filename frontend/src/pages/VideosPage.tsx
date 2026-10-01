import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SearchX } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type VideoQuery } from "@/api/endpoints";
import { VideoTable } from "@/components/VideoTable";
import { Button, Card, EmptyState, ErrorState, FilterBar, Segmented } from "@/components/ui";
import { isoDate } from "@/lib/format";

const PAGE_SIZE = 25;
const STATUSES = [
  { value: "", label: "All" },
  { value: "pass", label: "Pass" },
  { value: "review", label: "Review" },
  { value: "fail", label: "Fail" },
  { value: "pending", label: "Pending" },
];
const RANGES: Record<string, { label: string; days: number | null }> = {
  "": { label: "Any time", days: null },
  today: { label: "Today", days: 0 },
  "7d": { label: "Last 7 days", days: 6 },
  "30d": { label: "Last 30 days", days: 29 },
};

function dateFrom(range: string): string | undefined {
  const days = RANGES[range]?.days;
  if (days === null || days === undefined) return undefined;
  const d = new Date();
  d.setDate(d.getDate() - days);
  return isoDate(d);
}

export function VideosPage() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const type = params.get("type") ?? "";
  const range = params.get("range") ?? "";
  const q = params.get("q") ?? "";
  const page = Math.max(1, Number(params.get("page") ?? 1) || 1);
  const [search, setSearch] = useState(q);
  useEffect(() => setSearch(q), [q]);

  const update = (patch: Record<string, string>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    if (!("page" in patch)) next.delete("page");
    setParams(next, { replace: true });
  };

  const query: VideoQuery = {
    status: status || undefined,
    process_type: type || undefined,
    q: q || undefined,
    date_from: dateFrom(range),
    page,
    page_size: PAGE_SIZE,
  };
  const videos = useQuery({
    queryKey: ["videos", query],
    queryFn: () => api.videos(query),
    placeholderData: keepPreviousData,
  });
  const data = videos.data;
  const filtered = Boolean(status || type || range || q);
  const first = data && data.total ? (data.page - 1) * data.page_size + 1 : 0;
  const last = data ? Math.min(data.total, data.page * data.page_size) : 0;

  return (
    <>
      <FilterBar>
        <Segmented
          label="Status"
          value={status}
          onChange={(v) => update({ status: v })}
          options={STATUSES}
        />
        <select
          aria-label="Process type"
          className="select"
          value={type}
          onChange={(e) => update({ type: e.target.value })}
        >
          <option value="">All types</option>
          <option value="Forward">Forward</option>
          <option value="Return">Return</option>
        </select>
        <select
          aria-label="Date range"
          className="select"
          value={range}
          onChange={(e) => update({ range: e.target.value })}
        >
          {Object.entries(RANGES).map(([k, r]) => (
            <option key={k} value={k}>
              {r.label}
            </option>
          ))}
        </select>
        <form
          className="flex min-w-[180px] flex-1 gap-2 md:max-w-[300px]"
          onSubmit={(e) => {
            e.preventDefault();
            update({ q: search.trim() });
          }}
        >
          <input
            type="search"
            aria-label="Search AWB, barcode or file"
            placeholder="AWB, barcode, file…"
            className="input min-w-0 flex-1 py-1.5"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Button type="submit">Search</Button>
        </form>
      </FilterBar>
      <Card className="overflow-hidden">
        {videos.isError ? (
          <ErrorState error={videos.error} onRetry={() => videos.refetch()} />
        ) : (
          <VideoTable
            full
            rows={data?.items}
            loading={videos.isPending}
            empty={
              filtered ? (
                <EmptyState
                  icon={SearchX}
                  title="No inspections match these filters."
                  action={
                    <Button onClick={() => setParams({}, { replace: true })}>Clear filters</Button>
                  }
                />
              ) : (
                <EmptyState
                  icon={SearchX}
                  title="No inspections yet. Upload your first video."
                  action={
                    <Link to="/upload" className="font-medium text-accent-text hover:underline">
                      Upload videos
                    </Link>
                  }
                />
              )
            }
          />
        )}
        {data && data.total > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-[18px] py-3">
            <span className="text-sm text-text-2" aria-live="polite">
              Showing {first}–{last} of {data.total.toLocaleString()}
            </span>
            <div className="flex gap-2">
              <Button disabled={page <= 1} onClick={() => update({ page: String(page - 1) })}>
                Previous
              </Button>
              <Button
                disabled={last >= data.total}
                onClick={() => update({ page: String(page + 1) })}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>
    </>
  );
}
