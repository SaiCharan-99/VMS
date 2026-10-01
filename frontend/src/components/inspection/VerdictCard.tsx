import { Card, CardBody, ScoreRing, StatusBadge } from "@/components/ui";
import type { Status } from "@/types/analysis";

export function VerdictCard({
  status,
  score,
  summary,
  confidence,
  awb,
  framesOk,
  framesSampled,
  human,
}: {
  status: Status;
  score: number;
  summary: string;
  confidence: number;
  awb: string | null;
  framesOk?: number;
  framesSampled?: number;
  human?: boolean;
}) {
  return (
    <Card>
      <CardBody className="flex items-center gap-[18px]">
        <ScoreRing score={score} status={status} />
        <div className="min-w-0 flex-1">
          <StatusBadge status={status} variant="verdict" human={human} />
          <p className="m-0 mt-1.5 text-[13px] text-text-2">{summary}</p>
        </div>
      </CardBody>
      <dl className="m-0 grid grid-cols-2 gap-px border-t border-border bg-border sm:grid-cols-3">
        <div className="bg-surface px-[18px] py-3">
          <dt className="text-text-3">Confidence</dt>
          <dd className="m-0 mt-0.5 font-semibold">{Math.round(confidence * 100)}%</dd>
        </div>
        <div className="bg-surface px-[18px] py-3">
          <dt className="text-text-3">AWB</dt>
          <dd className="mono m-0 mt-0.5 break-all font-semibold">{awb ?? "—"}</dd>
        </div>
        <div className="col-span-2 bg-surface px-[18px] py-3 sm:col-span-1">
          <dt className="text-text-3">Frames OK</dt>
          <dd className="tabular m-0 mt-0.5 font-semibold">
            {framesOk !== undefined && framesSampled !== undefined
              ? `${framesOk} / ${framesSampled}`
              : "—"}
          </dd>
        </div>
      </dl>
    </Card>
  );
}
