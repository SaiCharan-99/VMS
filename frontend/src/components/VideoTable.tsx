import { Film, Video as VideoIcon } from "lucide-react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { DataTable, EmptyState, StatusBadge, type Column } from "@/components/ui";
import { formatWhen } from "@/lib/format";
import type { Video } from "@/types/api";

const COLUMNS: Record<string, Column<Video>> = {
  video: {
    key: "video",
    header: "Video",
    cell: (v) => (
      <div className="flex min-w-0 items-center gap-2.5">
        <div
          aria-hidden
          className="hidden h-[30px] w-11 flex-none place-items-center rounded bg-surface-2 text-text-3 sm:grid"
        >
          <Film size={14} strokeWidth={1.8} />
        </div>
        <span className="block max-w-[150px] truncate font-medium sm:max-w-[220px] md:max-w-[260px]">
          {v.original_filename}
        </span>
      </div>
    ),
  },
  awb: {
    key: "awb",
    header: "AWB",
    secondary: true,
    cell: (v) => <span className="mono text-text-2">{v.awb ?? "—"}</span>,
  },
  type: {
    key: "type",
    header: "Type",
    secondary: true,
    cell: (v) => <span className="chip">{v.process_type}</span>,
  },
  operator: {
    key: "operator",
    header: "Operator",
    secondary: true,
    cell: (v) => (
      <span className="text-text-2">
        {v.uploaded_by_name ?? (v.source === "api" ? "API" : "—")}
      </span>
    ),
  },
  uploaded: {
    key: "uploaded",
    header: "Uploaded",
    secondary: true,
    cell: (v) => <span className="whitespace-nowrap text-text-2">{formatWhen(v.created_at)}</span>,
  },
  score: {
    key: "score",
    header: "Score",
    numeric: true,
    cell: (v) => <span className="font-semibold">{v.latest_analysis?.total_score ?? "—"}</span>,
  },
  status: {
    key: "status",
    header: "Status",
    cell: (v) => <StatusBadge status={v.final_status} human={v.human_reviewed} />,
  },
};

export function VideoTable({
  rows,
  loading,
  full,
  empty,
}: {
  rows: Video[] | undefined;
  loading: boolean;
  /** The Inspections page shows operator and upload time too. */
  full?: boolean;
  empty?: ReactNode;
}) {
  const navigate = useNavigate();
  const keys = full
    ? ["video", "awb", "type", "operator", "uploaded", "score", "status"]
    : ["video", "awb", "type", "score", "status"];
  return (
    <DataTable
      caption="Inspections"
      columns={keys.map((k) => COLUMNS[k] as Column<Video>)}
      rows={rows}
      rowKey={(v) => v.id}
      loading={loading}
      onRowClick={(v) => navigate(`/videos/${v.id}`)}
      rowLabel={(v) => `Open ${v.original_filename}`}
      empty={
        empty ?? (
          <EmptyState icon={VideoIcon} title="No inspections yet. Upload your first video." />
        )
      }
    />
  );
}
