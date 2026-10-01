import { UserCheck } from "lucide-react";
import { SHORT_LABEL, VERDICT_LABEL, type BadgeStatus } from "@/lib/copy";
import { cn } from "@/lib/cn";

const TONE: Record<BadgeStatus, string> = {
  pass: "bg-pass-soft text-pass",
  review: "bg-review-soft text-review",
  fail: "bg-fail-soft text-fail",
  pending: "bg-surface-2 text-text-2",
};

export interface StatusBadgeProps {
  status: BadgeStatus;
  /** "verdict" uses Accepted / Review required / Rejected (detail pages). */
  variant?: "short" | "verdict";
  /** A reviewer decided this, overriding the model. */
  human?: boolean;
  /** Extra text after the label, e.g. the score. */
  suffix?: string;
  className?: string;
}

export function StatusBadge({
  status,
  variant = "short",
  human,
  suffix,
  className,
}: StatusBadgeProps) {
  const label =
    variant === "verdict" && status !== "pending" ? VERDICT_LABEL[status] : SHORT_LABEL[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-[9px] py-0.5 text-xs font-semibold",
        TONE[status],
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {label}
      {suffix && <span>· {suffix}</span>}
      {human && <UserCheck size={13} strokeWidth={2} aria-label="Decided by a reviewer" />}
    </span>
  );
}
