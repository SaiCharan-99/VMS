import { cn } from "@/lib/cn";

export function Bar({
  value,
  tone = "accent",
  label,
  className,
}: {
  /** 0..1 */
  value: number;
  tone?: "accent" | "pass" | "review" | "fail" | "muted";
  label?: string;
  className?: string;
}) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const color = {
    accent: "bg-accent",
    pass: "bg-pass",
    review: "bg-review",
    fail: "bg-fail",
    muted: "bg-text-3",
  }[tone];
  return (
    <div
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className={cn("h-1.5 overflow-hidden rounded-full bg-surface-2", className)}
    >
      <div
        className={cn("h-full rounded-full transition-[width]", color)}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
