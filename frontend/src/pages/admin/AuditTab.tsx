import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ScrollText } from "lucide-react";
import { useState } from "react";
import { api, type AuditQuery } from "@/api/endpoints";
import {
  Button,
  Card,
  DataTable,
  EmptyState,
  ErrorState,
  FilterBar,
  type Column,
} from "@/components/ui";
import { formatWhen } from "@/lib/format";
import type { AuditEntry } from "@/types/api";

const ACTIONS = [
  "auth.",
  "video.",
  "analysis.",
  "review.",
  "user.",
  "api_key.",
  "warehouse.",
  "station.",
];
const PAGE_SIZE = 50;

function summarize(data: AuditEntry["data"]): string {
  if (!data) return "";
  return Object.entries(data)
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
    .join(" · ");
}

export function AuditTab() {
  const [q, setQ] = useState<AuditQuery>({ page: 1, page_size: PAGE_SIZE });
  const log = useQuery({
    queryKey: ["admin", "audit", q],
    queryFn: () => api.admin.auditLog(q),
    placeholderData: keepPreviousData,
  });
  const users = useQuery({ queryKey: ["admin", "users"], queryFn: api.admin.users });
  const keys = useQuery({ queryKey: ["admin", "api-keys"], queryFn: api.admin.apiKeys });
  const userName = new Map(users.data?.items.map((u) => [u.id, u.name]));
  const keyName = new Map(keys.data?.map((k) => [k.id, k.name]));
  const set = (patch: Partial<AuditQuery>) => setQ({ ...q, ...patch, page: 1 });

  const columns: Column<AuditEntry>[] = [
    {
      key: "when",
      header: "When",
      cell: (e) => (
        <span className="whitespace-nowrap text-text-2" title={e.created_at}>
          {formatWhen(e.created_at)}
        </span>
      ),
    },
    {
      key: "actor",
      header: "Actor",
      secondary: true,
      cell: (e) => (
        <span className="text-text-2">
          {e.actor_user_id
            ? (userName.get(e.actor_user_id) ?? `User ${e.actor_user_id}`)
            : e.actor_api_key_id
              ? `Key: ${keyName.get(e.actor_api_key_id) ?? e.actor_api_key_id}`
              : "System"}
        </span>
      ),
    },
    { key: "action", header: "Action", cell: (e) => <span className="mono">{e.action}</span> },
    {
      key: "entity",
      header: "Entity",
      cell: (e) => (
        <span className="mono text-text-2">
          {e.entity_type}
          {e.entity_id ? ` #${e.entity_id}` : ""}
        </span>
      ),
    },
    {
      key: "data",
      header: "Details",
      secondary: true,
      cell: (e) => (
        <span
          className="block max-w-[420px] truncate text-xs text-text-2"
          title={summarize(e.data)}
        >
          {summarize(e.data)}
        </span>
      ),
    },
  ];

  const total = log.data?.total ?? 0;
  const page = q.page ?? 1;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <FilterBar>
        <select
          className="select"
          aria-label="Action"
          value={q.action ?? ""}
          onChange={(e) => set({ action: e.target.value || undefined })}
        >
          <option value="">All actions</option>
          {ACTIONS.map((a) => (
            <option key={a} value={a}>
              {a.slice(0, -1)}
            </option>
          ))}
        </select>
        <input
          className="input py-1.5"
          aria-label="Entity id"
          placeholder="Entity id"
          value={q.entity_id ?? ""}
          onChange={(e) => set({ entity_id: e.target.value || undefined })}
        />
        <input
          type="date"
          className="input py-1.5"
          aria-label="From date"
          value={q.date_from ?? ""}
          onChange={(e) => set({ date_from: e.target.value || undefined })}
        />
        <input
          type="date"
          className="input py-1.5"
          aria-label="To date"
          value={q.date_to ?? ""}
          onChange={(e) => set({ date_to: e.target.value || undefined })}
        />
      </FilterBar>
      <Card className="overflow-hidden">
        {log.isError ? (
          <ErrorState error={log.error} onRetry={() => log.refetch()} />
        ) : (
          <DataTable
            caption="Audit log, newest first"
            columns={columns}
            rows={log.data?.items}
            rowKey={(e) => e.id}
            loading={log.isPending}
            empty={<EmptyState icon={ScrollText} title="No audit entries match these filters." />}
          />
        )}
      </Card>
      <div className="mt-3 flex items-center justify-end gap-2 text-sm text-text-2">
        <span className="tabular">
          Page {page} of {pages} · {total.toLocaleString()} entries
        </span>
        <Button size="sm" disabled={page <= 1} onClick={() => setQ({ ...q, page: page - 1 })}>
          Previous
        </Button>
        <Button size="sm" disabled={page >= pages} onClick={() => setQ({ ...q, page: page + 1 })}>
          Next
        </Button>
      </div>
    </>
  );
}
