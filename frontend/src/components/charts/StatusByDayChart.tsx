import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";
import { SHORT_LABEL } from "@/lib/copy";
import { dayLabel } from "@/lib/format";
import type { ReportGroup } from "@/types/api";
import { useTokens } from "./useTokens";

const SERIES = ["pass", "review", "fail"] as const;

function TipBox({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload as ReportGroup;
  return (
    <div className="rounded-ctl border border-border bg-surface px-3 py-2 text-xs shadow-card">
      <div className="mb-1 font-semibold text-text">{dayLabel(String(label))}</div>
      {SERIES.map((s) => (
        <div key={s} className="tabular flex justify-between gap-4 text-text-2">
          <span>{SHORT_LABEL[s]}</span>
          <span className="text-text">{row[s]}</span>
        </div>
      ))}
      {row.pending > 0 && (
        <div className="tabular flex justify-between gap-4 text-text-3">
          <span>Analyzing</span>
          <span>{row.pending}</span>
        </div>
      )}
    </div>
  );
}

/** Stacked outcome per day in the reserved status colours. Review is hatched so it stays
 *  distinguishable from Fail for colour-blind readers; a legend and a table view back it up. */
export function StatusByDayChart({
  groups,
  height = 220,
}: {
  groups: ReportGroup[];
  height?: number;
}) {
  const t = useTokens();
  const fill = { pass: t.pass, review: "url(#hatch-review)", fail: t.fail };
  return (
    <div>
      <ul
        className="m-0 mb-2 flex list-none flex-wrap gap-3.5 p-0 text-xs text-text-2"
        aria-label="Legend"
      >
        {SERIES.map((s) => (
          <li key={s} className="flex items-center gap-1.5">
            <svg width="10" height="10" aria-hidden>
              <rect width="10" height="10" rx="2" fill={t[s]} />
              {s === "review" && <path d="M0 10 L10 0" stroke={t.surface} strokeWidth="1.5" />}
            </svg>
            {SHORT_LABEL[s]}
          </li>
        ))}
      </ul>
      <div
        style={{ height }}
        role="img"
        aria-label="Outcomes per day, stacked: pass, review, fail. A table view follows."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={groups}
            margin={{ top: 4, right: 4, bottom: 0, left: -18 }}
            barCategoryGap="22%"
          >
            <defs>
              <pattern
                id="hatch-review"
                width="6"
                height="6"
                patternUnits="userSpaceOnUse"
                patternTransform="rotate(45)"
              >
                <rect width="6" height="6" fill={t.review} />
                <line
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="6"
                  stroke={t.surface}
                  strokeWidth="2"
                  strokeOpacity="0.55"
                />
              </pattern>
            </defs>
            <CartesianGrid vertical={false} stroke={t.border} />
            <XAxis
              dataKey="key"
              tickFormatter={dayLabel}
              tick={{ fill: t["text-3"], fontSize: 11.5 }}
              axisLine={{ stroke: t.border }}
              tickLine={false}
              minTickGap={8}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: t["text-3"], fontSize: 11.5 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              content={<TipBox />}
              cursor={{ fill: t.border, fillOpacity: 0.35 }}
              isAnimationActive={false}
            />
            {SERIES.map((s, i) => (
              <Bar
                key={s}
                dataKey={s}
                stackId="status"
                fill={fill[s]}
                stroke={t.surface}
                strokeWidth={2}
                radius={i === SERIES.length - 1 ? [4, 4, 0, 0] : 0}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
