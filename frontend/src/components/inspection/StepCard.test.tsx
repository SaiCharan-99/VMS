import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Step } from "@/types/analysis";
import { StepCard } from "./StepCard";

const step: Step = {
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
  notes: [],
  evidence: [],
};

describe("StepCard", () => {
  it("shows points and plain-language checks; metric keys only when expanded", async () => {
    render(
      <StepCard
        index={3}
        step={step}
        description="Tags shown close to camera"
        evidence={[]}
        onSeek={() => {}}
      />,
    );
    expect(screen.getByRole("heading", { name: "Brand Tag & Hangtag" })).toBeInTheDocument();
    expect(screen.getByText("15/25")).toBeInTheDocument();
    expect(screen.getByText("Brand tag visible")).toBeInTheDocument();
    expect(screen.getByText("Tag text not readable.")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "60");
    expect(screen.queryByText("avg_text_blocks")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Details" }));
    expect(screen.getByText("avg_text_blocks")).toBeInTheDocument();
    expect(screen.getByText("0/10")).toBeInTheDocument();
  });

  it("seeks to an evidence thumbnail timestamp", async () => {
    const onSeek = vi.fn();
    render(
      <StepCard
        index={1}
        step={step}
        evidence={[{ id: 1, step_key: "tags", kind: "tag", t_s: 24.4, url: "/api/v1/evidence/1" }]}
        onSeek={onSeek}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Jump to evidence at 0:24" }));
    expect(onSeek).toHaveBeenCalledWith(24.4);
  });
});
