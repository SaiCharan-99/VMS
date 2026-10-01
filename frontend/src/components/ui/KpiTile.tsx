import type { ReactNode } from "react";
import { Card } from "./Card";
import { cn } from "@/lib/cn";

export interface KpiTileProps {
  label: string;
  value: ReactNode;
  /** Text under the value; `trend` colours it (good = green, bad = red). */
  delta?: string;
  trend?: "good" | "bad" | "neutral";
  /** Extra content under the delta, e.g. a sparkline. */
  children?: ReactNode;
}

export function KpiTile({ label, value, delta, trend = "neutral", children }: KpiTileProps) {
  return (
    <Card className="px-[18px] py-4">
      <div className="text-[12.5px] text-text-2">{label}</div>
      <div className="tabular mt-1 text-[26px] font-semibold tracking-tight">{value}</div>
      {delta && (
        <div
          className={cn(
            "mt-0.5 text-xs",
            trend === "good" ? "text-pass" : trend === "bad" ? "text-fail" : "text-text-3",
          )}
        >
          {delta}
        </div>
      )}
      {children}
    </Card>
  );
}
