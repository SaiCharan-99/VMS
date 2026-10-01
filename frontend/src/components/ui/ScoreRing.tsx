import type { BadgeStatus } from "@/lib/copy";

const COLOR: Record<BadgeStatus, string> = {
  pass: "var(--pass)",
  review: "var(--review)",
  fail: "var(--fail)",
  pending: "var(--text-3)",
};

export function ScoreRing({ score, status }: { score: number; status: BadgeStatus }) {
  const p = Math.max(0, Math.min(100, Math.round(score)));
  return (
    <div
      role="img"
      aria-label={`Score ${p} out of 100`}
      className="grid h-[76px] w-[76px] flex-none place-items-center rounded-full"
      style={{ background: `conic-gradient(${COLOR[status]} ${p}%, var(--surface-2) 0)` }}
    >
      <div className="tabular grid h-[62px] w-[62px] place-items-center rounded-full bg-surface text-xl font-bold">
        {p}
      </div>
    </div>
  );
}
