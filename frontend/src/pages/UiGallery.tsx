import { Inbox } from "lucide-react";
import { useState } from "react";
import { EvidenceTimeline } from "@/components/inspection/EvidenceTimeline";
import { StepCard } from "@/components/inspection/StepCard";
import { VerdictCard } from "@/components/inspection/VerdictCard";
import {
  Bar,
  Button,
  Card,
  CardBody,
  CardHeader,
  DataTable,
  Dialog,
  EmptyState,
  FilterBar,
  Kbd,
  KpiTile,
  ScoreRing,
  Segmented,
  Skeleton,
  StatusBadge,
  useToast,
} from "@/components/ui";
import type { Step } from "@/types/analysis";

const STEP: Step = {
  key: "tags",
  title: "Brand Tag & Hangtag",
  weight: 25,
  score: 15,
  status: "partial",
  checks: [
    {
      key: "tag_visible",
      passed: true,
      points: 15,
      max_points: 15,
      metric: "tag_ratio",
      value: 0.18,
      threshold: 0.1,
    },
    {
      key: "tag_readable",
      passed: false,
      points: 0,
      max_points: 10,
      metric: "avg_text_blocks",
      value: 2.1,
      threshold: 3,
      note: "Tag text not readable.",
    },
  ],
  notes: ["Tag text not readable."],
  evidence: [],
};

/** Dev-only component gallery (route /_ui). Use the theme toggle in the top bar to check both themes. */
export function UiGallery() {
  const [seg, setSeg] = useState("all");
  const [open, setOpen] = useState(false);
  const toast = useToast();
  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader title="Buttons" actions={<Kbd>⌘K</Kbd>} />
        <CardBody className="flex flex-wrap gap-2">
          <Button variant="primary">Primary</Button>
          <Button>Secondary</Button>
          <Button variant="pass">Pass</Button>
          <Button variant="fail">Fail</Button>
          <Button variant="ghost">Ghost</Button>
          <Button size="sm">Small</Button>
          <Button loading>Loading</Button>
          <Button onClick={() => toast("Saved.")}>Toast</Button>
          <Button onClick={() => toast("Something failed.", "error")}>Error toast</Button>
          <Button onClick={() => setOpen(true)}>Dialog</Button>
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Status" />
        <CardBody className="flex flex-wrap items-center gap-3">
          <StatusBadge status="pass" />
          <StatusBadge status="review" />
          <StatusBadge status="fail" />
          <StatusBadge status="pending" />
          <StatusBadge status="pass" variant="verdict" human />
          <StatusBadge status="review" variant="verdict" />
          <StatusBadge status="fail" variant="verdict" />
          <ScoreRing score={88} status="pass" />
          <ScoreRing score={64} status="review" />
          <ScoreRing score={31} status="fail" />
        </CardBody>
      </Card>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiTile label="Inspected today" value="412" delta="▲ 8% vs last Tue" trend="good" />
        <KpiTile label="Pass rate" value="86.4%" delta="▼ 1.4 pts" trend="bad" />
        <KpiTile label="Awaiting review" value="14" delta="oldest 38 min" />
        <KpiTile label="Loading" value={<Skeleton className="mt-1 h-7 w-16" />} />
      </div>
      <Card>
        <CardHeader title="FilterBar, bars, empty" />
        <CardBody className="grid gap-3">
          <FilterBar end={<Button>Export CSV</Button>}>
            <Segmented
              label="Status"
              value={seg}
              onChange={setSeg}
              options={[
                { value: "all", label: "All" },
                { value: "pass", label: "Pass" },
                { value: "review", label: "Review" },
              ]}
            />
            <select aria-label="Type" className="select">
              <option>All types</option>
            </select>
          </FilterBar>
          <Bar value={0.24} tone="muted" label="Uploading" />
          <Bar value={0.58} label="Analyzing" />
          <Bar value={1} tone="pass" label="Done" />
          <EmptyState icon={Inbox} title="No inspections yet. Upload your first video." />
        </CardBody>
      </Card>
      <Card className="overflow-hidden">
        <DataTable
          caption="Demo"
          loading
          rows={[]}
          rowKey={() => 1}
          columns={[
            { key: "a", header: "Video", cell: () => null },
            { key: "b", header: "Score", numeric: true, cell: () => null },
          ]}
        />
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <div className="aspect-video rounded-card bg-[#1d1f24]" />
          <EvidenceTimeline
            duration={42}
            current={13}
            onSeek={() => {}}
            markers={[
              { id: 1, t: 3, step: 1, status: "pass", label: "Label" },
              { id: 2, t: 24, step: 3, status: "review", label: "Tag" },
            ]}
          />
        </div>
        <div className="grid gap-4">
          <VerdictCard
            status="pass"
            score={88}
            summary="Return recording passed. Weakest area: brand tags (72%)."
            confidence={0.81}
            awb="AWB123456789"
            framesOk={119}
            framesSampled={127}
          />
          <Card>
            <StepCard
              index={3}
              step={STEP}
              description="Brand labels and price tags shown close to camera"
              evidence={[]}
              onSeek={() => {}}
            />
          </Card>
        </div>
      </div>
      <Dialog
        open={open}
        title="Example dialog"
        onClose={() => setOpen(false)}
        footer={
          <>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button variant="primary" onClick={() => setOpen(false)}>
              OK
            </Button>
          </>
        }
      >
        Focus stays inside until it closes.
      </Dialog>
    </div>
  );
}
