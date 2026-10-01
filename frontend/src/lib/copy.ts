import type { Check, Status, StepStatus } from "@/types/analysis";

export type BadgeStatus = Status | "pending";

export const SHORT_LABEL: Record<BadgeStatus, string> = {
  pass: "Pass",
  review: "Review",
  fail: "Fail",
  pending: "Analyzing",
};

export const VERDICT_LABEL: Record<Status, string> = {
  pass: "Accepted",
  review: "Review required",
  fail: "Rejected",
};

export const STEP_TO_STATUS: Record<StepStatus, Status> = {
  met: "pass",
  partial: "review",
  missed: "fail",
};

// Plain-language label for a check that passed (failed checks use the rubric's fail_note).
const CHECK_LABEL: Record<string, string> = {
  label_text_visible: "Label text readable",
  label_held: "Label held steady",
  barcode_read: "Barcode read",
  package_visible: "Package visible",
  six_sides: "All 6 sides shown",
  long_enough: "Long enough for the full process",
  sealing_motion: "Sealing shown at the end",
  tag_visible: "Brand tag visible",
  tag_readable: "Tag text readable",
  product_visible: "Product visible",
  product_turned: "Both sides of the product shown",
};

function humanize(key: string): string {
  const s = key.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function checkText(check: Check): string {
  if (!check.passed && check.note) return check.note;
  const label = CHECK_LABEL[check.key] ?? humanize(check.key);
  if (check.passed) return label;
  return check.points > 0 ? `${label} (partly)` : `${label}: not met`;
}

export function isFullResult<T extends { schema_version: string }>(r: unknown): r is T {
  return (
    typeof r === "object" &&
    r !== null &&
    (r as { schema_version?: unknown }).schema_version === "2.0"
  );
}
