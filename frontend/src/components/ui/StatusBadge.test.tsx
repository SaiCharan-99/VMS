import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge (verdict badge)", () => {
  it.each([
    ["pass", "Pass", "Accepted"],
    ["review", "Review", "Review required"],
    ["fail", "Fail", "Rejected"],
  ] as const)("%s shows %s / %s", (status, short, verdict) => {
    const { rerender } = render(<StatusBadge status={status} />);
    expect(screen.getByText(short)).toBeInTheDocument();
    rerender(<StatusBadge status={status} variant="verdict" />);
    expect(screen.getByText(verdict)).toBeInTheDocument();
  });

  it("shows Analyzing for pending and marks human overrides", () => {
    render(<StatusBadge status="pending" human />);
    expect(screen.getByText("Analyzing")).toBeInTheDocument();
    expect(screen.getByLabelText("Decided by a reviewer")).toBeInTheDocument();
  });
});
