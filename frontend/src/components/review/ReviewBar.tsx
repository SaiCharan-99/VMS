import { forwardRef } from "react";
import { Button, Kbd } from "@/components/ui";
import { REASON_LABEL } from "@/lib/copy";
import type { ReviewDraft } from "@/lib/review";
import { REASON_CODES, type ReasonCode } from "@/types/api";

/** Sticky decision bar: reason, comment, Fail / Pass with key hints. */
export const ReviewBar = forwardRef<
  HTMLSelectElement,
  {
    draft: ReviewDraft;
    onChange: (d: ReviewDraft) => void;
    onDecide: (decision: "pass" | "fail") => void;
    busy: boolean;
    error?: string | null;
  }
>(function ReviewBar({ draft, onChange, onDecide, busy, error }, reasonRef) {
  return (
    <div className="sticky bottom-0 z-10 mt-4">
      <div
        role="group"
        aria-label="Review decision"
        className="flex flex-wrap items-center gap-2.5 rounded-card border border-border bg-surface px-[18px] py-3.5 shadow-card"
      >
        <select
          ref={reasonRef}
          className="select min-w-0 flex-1 sm:flex-none"
          aria-label="Reason"
          value={draft.reason}
          onChange={(e) => onChange({ ...draft, reason: e.target.value as ReasonCode | "" })}
        >
          <option value="">Reason…</option>
          {REASON_CODES.map((c) => (
            <option key={c} value={c}>
              {REASON_LABEL[c]}
            </option>
          ))}
        </select>
        <input
          className="input min-w-[120px] flex-1"
          aria-label="Comment"
          placeholder="Comment (required for Other or to overturn the model)"
          value={draft.comment}
          maxLength={2000}
          onChange={(e) => onChange({ ...draft, comment: e.target.value })}
        />
        <Button variant="fail" onClick={() => onDecide("fail")} disabled={busy}>
          Fail <Kbd>F</Kbd>
        </Button>
        <Button variant="pass" onClick={() => onDecide("pass")} disabled={busy}>
          Pass <Kbd>P</Kbd>
        </Button>
      </div>
      {error && (
        <p role="alert" className="m-0 mt-2 text-sm text-fail">
          {error}
        </p>
      )}
    </div>
  );
});
