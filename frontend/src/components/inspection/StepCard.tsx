import { ChevronRight } from "lucide-react";
import { useId, useState } from "react";
import { Bar } from "@/components/ui";
import { apiUrl } from "@/api/client";
import { cn } from "@/lib/cn";
import { checkText, STEP_TO_STATUS } from "@/lib/copy";
import { formatDuration, formatMetric } from "@/lib/format";
import type { Step } from "@/types/analysis";
import type { Evidence } from "@/types/api";

const CIRCLE = { pass: "bg-pass", review: "bg-review", fail: "bg-fail" } as const;

export function StepCard({
  index,
  step,
  description,
  evidence,
  onSeek,
}: {
  index: number;
  step: Step;
  description?: string;
  evidence: Evidence[];
  onSeek: (t: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const detailsId = useId();
  const status = STEP_TO_STATUS[step.status];
  const ratio = step.weight > 0 ? step.score / step.weight : 0;

  return (
    <section
      aria-label={`Step ${index}: ${step.title}`}
      className="border-t border-border px-[18px] py-3.5 first:border-t-0"
    >
      <div className="flex items-center gap-2.5">
        <span
          aria-hidden
          className={cn(
            "grid h-[22px] w-[22px] flex-none place-items-center rounded-full text-[11px] font-bold text-on-status",
            CIRCLE[status],
          )}
        >
          {index}
        </span>
        <h3 className="m-0 flex-1 text-base font-semibold">{step.title}</h3>
        <span
          className="tabular text-[13px] text-text-2"
          aria-label={`${step.score} of ${step.weight} points`}
        >
          {step.score}/{step.weight}
        </span>
      </div>
      <div className="pl-8">
        {description && <p className="mb-2.5 mt-1 text-[12.5px] text-text-3">{description}</p>}
        <Bar
          value={ratio}
          tone={status}
          label={`${step.title}: ${Math.round(ratio * 100)}%`}
          className={description ? "" : "mt-2.5"}
        />
        <ul className="m-0 mt-2.5 grid list-none gap-1.5 p-0">
          {step.checks.map((c) => (
            <li key={c.key} className="flex items-baseline gap-2 text-[13px]">
              <span aria-hidden className={c.passed ? "text-pass" : "font-bold text-review"}>
                {c.passed ? "✓" : "!"}
              </span>
              <span className={c.passed ? "text-text-2" : "text-text"}>
                <span className="sr-only">{c.passed ? "Passed: " : "Needs attention: "}</span>
                {checkText(c)}
              </span>
            </li>
          ))}
        </ul>
        {evidence.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-2">
            {evidence.map((e) => (
              <button
                key={e.id}
                type="button"
                onClick={() => onSeek(e.t_s)}
                aria-label={`Jump to evidence at ${formatDuration(e.t_s)}`}
                className="relative h-10 w-16 overflow-hidden rounded bg-surface-2"
              >
                <img
                  src={apiUrl(e.url)}
                  alt=""
                  loading="lazy"
                  className="h-full w-full object-cover"
                />
                <span className="absolute bottom-0.5 right-[3px] rounded-[3px] bg-black/65 px-1 font-mono text-[10px] text-white">
                  {formatDuration(e.t_s)}
                </span>
              </button>
            ))}
          </div>
        )}
        <button
          type="button"
          aria-expanded={open}
          aria-controls={detailsId}
          onClick={() => setOpen((o) => !o)}
          className="mt-2 inline-flex items-center gap-1 rounded text-xs font-medium text-text-2 hover:text-text"
        >
          <ChevronRight
            size={14}
            aria-hidden
            className={cn("transition-transform", open && "rotate-90")}
          />
          Details
        </button>
        {open && (
          <div id={detailsId} className="mt-2 overflow-x-auto">
            <table className="w-full border-collapse text-xs">
              <caption className="sr-only">Checks for {step.title}</caption>
              <thead>
                <tr className="text-left text-text-2">
                  <th scope="col" className="py-1 pr-3 font-medium">
                    Metric
                  </th>
                  <th scope="col" className="py-1 pr-3 text-right font-medium">
                    Value
                  </th>
                  <th scope="col" className="py-1 pr-3 text-right font-medium">
                    Threshold
                  </th>
                  <th scope="col" className="py-1 text-right font-medium">
                    Points
                  </th>
                </tr>
              </thead>
              <tbody>
                {step.checks.map((c) => (
                  <tr key={c.key} className="border-t border-border">
                    <td className="py-1 pr-3 font-mono">{c.metric}</td>
                    <td className="tabular py-1 pr-3 text-right">{formatMetric(c.value)}</td>
                    <td className="tabular py-1 pr-3 text-right">{formatMetric(c.threshold)}</td>
                    <td className="tabular py-1 text-right">
                      {c.points}/{c.max_points}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
