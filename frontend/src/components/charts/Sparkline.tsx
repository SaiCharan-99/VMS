import { Line, LineChart, ResponsiveContainer, Tooltip, YAxis, type TooltipProps } from "recharts";
import { useTokens } from "./useTokens";

export interface SparkPoint {
  label: string;
  value: number | null;
}

function Tip({ active, payload }: TooltipProps<number, string>) {
  const p = payload?.[0]?.payload as SparkPoint | undefined;
  if (!active || !p) return null;
  return (
    <div className="rounded-ctl border border-border bg-surface px-2 py-1 text-xs shadow-card">
      {p.label}:{" "}
      <span className="tabular font-semibold">{p.value === null ? "—" : `${p.value}%`}</span>
    </div>
  );
}

/** Tiny single-series trend in the accent colour (no axes; the tile names the measure). */
export function Sparkline({ points, label }: { points: SparkPoint[]; label: string }) {
  const t = useTokens();
  // A single day with data has no line to draw, so mark it with a dot instead.
  const lonely = points.filter((p) => p.value !== null).length < 2;
  return (
    <div className="mt-2 h-9" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
          <YAxis hide domain={[0, 100]} />
          <Tooltip content={<Tip />} cursor={{ stroke: t.border }} isAnimationActive={false} />
          <Line
            type="monotone"
            dataKey="value"
            stroke={t.accent}
            strokeWidth={2}
            dot={lonely ? { r: 3, fill: t.accent, stroke: t.surface, strokeWidth: 2 } : false}
            activeDot={{ r: 4, stroke: t.surface, strokeWidth: 2 }}
            connectNulls
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
