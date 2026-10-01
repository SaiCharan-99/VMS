import type { ReasonCode } from "@/types/api";

export interface ReviewDraft {
  reason: ReasonCode | "";
  comment: string;
}

/** Comment needed for "other" and whenever the decision overturns a model pass/fail. */
export function commentRequired(
  draft: ReviewDraft,
  decision: "pass" | "fail",
  modelStatus: string | undefined,
): boolean {
  const overturns = (modelStatus === "pass" || modelStatus === "fail") && modelStatus !== decision;
  return draft.reason === "other" || overturns;
}
