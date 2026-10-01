import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Skeleton } from "./Skeleton";

export interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  /** Right-aligned tabular numbers. */
  numeric?: boolean;
  /** Hidden below 760px. */
  secondary?: boolean;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading,
  skeletonRows = 5,
  empty,
  onRowClick,
  rowLabel,
  caption,
}: {
  columns: Column<T>[];
  rows: T[] | undefined;
  rowKey: (row: T) => string | number;
  loading?: boolean;
  skeletonRows?: number;
  empty?: ReactNode;
  /** Rows become keyboard-reachable links when set. */
  onRowClick?: (row: T) => void;
  rowLabel?: (row: T) => string;
  caption: string;
}) {
  const cellCls = (c: Column<T>) =>
    cn(
      "px-3 first:pl-4 last:pr-4 md:px-[18px] md:first:pl-[18px] md:last:pr-[18px]",
      c.numeric && "tabular text-right",
      c.secondary && "hidden md:table-cell",
    );
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <caption className="sr-only">{caption}</caption>
        <thead className="sticky top-0 z-[1]">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={cn(
                  cellCls(c),
                  "border-b border-border bg-surface-2 py-2.5 text-left text-xs font-medium text-text-2",
                  c.numeric && "text-right",
                )}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading &&
            Array.from({ length: skeletonRows }, (_, i) => (
              <tr key={`sk${i}`} className="border-b border-border last:border-b-0">
                {columns.map((c) => (
                  <td key={c.key} className={cn(cellCls(c), "py-3.5")}>
                    <Skeleton className="h-4 w-full max-w-[160px]" />
                  </td>
                ))}
              </tr>
            ))}
          {!loading &&
            rows?.map((row) => (
              <tr
                key={rowKey(row)}
                tabIndex={onRowClick ? 0 : undefined}
                aria-label={onRowClick && rowLabel ? rowLabel(row) : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onKeyDown={
                  onRowClick
                    ? (e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onRowClick(row);
                        }
                      }
                    : undefined
                }
                className={cn(
                  "border-b border-border last:border-b-0",
                  onRowClick &&
                    "cursor-pointer hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:-outline-offset-2",
                )}
              >
                {columns.map((c) => (
                  <td key={c.key} className={cn(cellCls(c), "py-3 align-middle")}>
                    {c.cell(row)}
                  </td>
                ))}
              </tr>
            ))}
        </tbody>
      </table>
      {!loading && rows && rows.length === 0 && empty}
    </div>
  );
}
