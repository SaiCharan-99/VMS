import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { detail, video } from "@/test/fixtures";
import { renderPage } from "@/test/render";
import { server } from "@/test/server";
import type { ReportSummary, Video } from "@/types/api";
import { AdminPage } from "./AdminPage";
import { ReportsPage } from "./ReportsPage";
import { ReviewPage } from "./ReviewPage";
import { VideoDetailPage } from "./VideoDetailPage";

const me = (role: string) =>
  http.get("/api/v1/auth/me", () =>
    HttpResponse.json({
      id: 7,
      email: "r@vms.local",
      name: "Rita R.",
      role,
      warehouse_id: null,
      is_active: true,
      created_at: "2026-10-01T00:00:00Z",
      last_login_at: null,
    }),
  );

const queued = (id: number, modelStatus = "review"): Video =>
  video({
    id,
    original_filename: `q${id}.mp4`,
    final_status: "review",
    latest_analysis: { ...video().latest_analysis!, status: modelStatus, total_score: 60 + id },
  });

describe("ReviewPage", () => {
  function setup(items: Video[]) {
    const posted: { id: number; body: Record<string, unknown> }[] = [];
    let queue = [...items];
    server.use(
      me("reviewer"),
      http.get("/api/v1/stations", () => HttpResponse.json([])),
      http.get("/api/v1/rubrics", () => HttpResponse.json([])),
      http.get("/api/v1/review-queue", () =>
        HttpResponse.json({ items: queue, total: queue.length, page: 1, page_size: 100 }),
      ),
      http.get("/api/v1/videos/:id", ({ params }) => {
        const v = items.find((x) => x.id === Number(params.id))!;
        const d = detail({ video: v });
        return HttpResponse.json({
          ...d,
          analysis: { ...d.analysis!, status: v.latest_analysis!.status },
        });
      }),
      http.get("/api/v1/videos/:id/stream", () => new HttpResponse(null, { status: 404 })),
      http.get("/api/v1/evidence/:id", () => new HttpResponse(null, { status: 404 })),
      http.post("/api/v1/videos/:id/reviews", async ({ params, request }) => {
        const id = Number(params.id);
        const body = (await request.json()) as Record<string, unknown>;
        posted.push({ id, body });
        queue = queue.filter((v) => v.id !== id);
        return HttpResponse.json(
          {
            id: posted.length,
            analysis_id: 9,
            reviewer_id: 7,
            reviewer_name: "Rita R.",
            final_status: body.final_status,
            reason_code: body.reason_code,
            comment: body.comment ?? null,
            created_at: new Date().toISOString(),
          },
          { status: 201 },
        );
      }),
    );
    renderPage(<ReviewPage />, { path: "/review" });
    return posted;
  }

  const focused = () => screen.findByRole("link", { name: /^q\d\.mp4$/ });

  it("clears the queue with the keyboard only: reason key, P/F, auto-advance", async () => {
    const posted = setup([queued(1), queued(2), queued(3)]);
    expect((await focused()).textContent).toBe("q1.mp4");

    fireEvent.keyDown(window, { key: "6" }); // Model was wrong
    fireEvent.keyDown(window, { key: "p" });
    await waitFor(() => expect(posted).toHaveLength(1));
    expect(posted[0]).toEqual({
      id: 1,
      body: { final_status: "pass", reason_code: "false_negative_model" },
    });
    await waitFor(() => expect(screen.getByRole("link", { name: "q2.mp4" })).toBeInTheDocument());

    fireEvent.keyDown(window, { key: "n" }); // skip q2
    expect(await screen.findByRole("link", { name: "q3.mp4" })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "1" });
    fireEvent.keyDown(window, { key: "f" });
    await waitFor(() => expect(posted).toHaveLength(2));
    expect(posted[1]).toEqual({
      id: 3,
      body: { final_status: "fail", reason_code: "label_unclear" },
    });
  });

  it("asks for a reason before deciding", async () => {
    const posted = setup([queued(1)]);
    await focused();
    fireEvent.keyDown(window, { key: "p" });
    expect(await screen.findByRole("alert")).toHaveTextContent("Choose a reason first");
    expect(posted).toHaveLength(0);
    expect(screen.getByRole("combobox", { name: "Reason" })).toHaveFocus();
  });

  it("requires a comment to overturn a model fail", async () => {
    const posted = setup([queued(1, "fail")]);
    await focused();
    fireEvent.keyDown(window, { key: "6" });
    fireEvent.keyDown(window, { key: "p" });
    expect(await screen.findByRole("alert")).toHaveTextContent("overturns the model");
    expect(posted).toHaveLength(0);

    const user = userEvent.setup();
    await user.type(screen.getByRole("textbox", { name: "Comment" }), "Seal visible at 0:12");
    await user.click(screen.getByRole("button", { name: /Pass/ }));
    await waitFor(() => expect(posted).toHaveLength(1));
    expect(posted[0]?.body.comment).toBe("Seal visible at 0:12");
  });

  it("shows an empty state when the queue is clear", async () => {
    setup([]);
    expect(await screen.findByText(/queue is clear/)).toBeInTheDocument();
  });
});

describe("VideoDetailPage review history", () => {
  it("lists decisions newest first with reviewer and reason", async () => {
    server.use(
      me("reviewer"),
      http.get("/api/v1/rubrics", () => HttpResponse.json([])),
      http.get("/api/v1/evidence/31", () => new HttpResponse(null, { status: 404 })),
      http.get("/api/v1/videos/1/stream", () => new HttpResponse(null, { status: 404 })),
      http.get("/api/v1/videos/1", () =>
        HttpResponse.json(
          detail({
            reviews: [
              {
                id: 1,
                analysis_id: 9,
                reviewer_id: 7,
                reviewer_name: "Rita R.",
                final_status: "fail",
                reason_code: "seal_not_shown",
                comment: null,
                created_at: "2026-09-10T10:00:00Z",
              },
              {
                id: 2,
                analysis_id: 9,
                reviewer_id: 8,
                reviewer_name: "Sam S.",
                final_status: "pass",
                reason_code: "false_negative_model",
                comment: "Seal at 0:12",
                created_at: "2026-09-10T11:00:00Z",
              },
            ],
          }),
        ),
      ),
    );
    renderPage(<VideoDetailPage />, { path: "/videos/:id", url: "/videos/1" });
    const card = (await screen.findByRole("heading", { name: "Review history" })).closest(
      "div",
    )!.parentElement!;
    const items = within(card).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Model was wrong (operator compliant)");
    expect(items[0]).toHaveTextContent("Sam S.");
    expect(items[0]).toHaveTextContent("Seal at 0:12");
    expect(items[1]).toHaveTextContent("Seal not shown");
  });
});

const summary = (over: Partial<ReportSummary> = {}): ReportSummary => ({
  date_from: "2026-09-25",
  date_to: "2026-10-01",
  group_by: "day",
  totals: { total: 7, pass: 3, review: 1, fail: 2, pending: 1 },
  analyzed: 6,
  pass_rate: 0.5,
  review_rate: 0.3333,
  reviewed: 3,
  agreement_rate: 0.5,
  agreement_n: 2,
  avg_score: 53.33,
  avg_turnaround_s: 1236,
  top_failed_checks: [
    {
      process_type: "Return",
      step_key: "shipping_label",
      check_key: "barcode_read",
      step_title: "Shipping Label & Barcode",
      note: "Barcode not read.",
      failures: 3,
      evaluated: 3,
      rate: 1,
    },
  ],
  groups: [
    {
      key: "2026-10-01",
      label: "2026-10-01",
      total: 7,
      pass: 3,
      review: 1,
      fail: 2,
      pending: 1,
      pass_rate: 0.5,
      avg_score: 53.33,
    },
  ],
  ...over,
});

describe("ReportsPage", () => {
  it("shows KPIs, top failed checks and the breakdown; filters reach the API", async () => {
    const seen: URLSearchParams[] = [];
    server.use(
      me("reviewer"),
      http.get("/api/v1/stations", () => HttpResponse.json([])),
      http.get("/api/v1/reports/summary", ({ request }) => {
        const sp = new URL(request.url).searchParams;
        seen.push(sp);
        const by = sp.get("group_by");
        if (by === "station") {
          return HttpResponse.json(
            summary({
              group_by: "station",
              groups: [{ ...summary().groups[0]!, key: "1", label: "ST-1" }],
            }),
          );
        }
        return HttpResponse.json(summary());
      }),
    );
    renderPage(<ReportsPage />, { path: "/reports", url: "/reports?range=30&process_type=Return" });
    expect(await screen.findByText("Model–reviewer agreement")).toBeInTheDocument();
    expect((await screen.findAllByText("50.0%")).length).toBeGreaterThanOrEqual(2); // pass + agreement
    expect(screen.getByText("Barcode read")).toBeInTheDocument();
    expect(await screen.findByRole("cell", { name: "ST-1" })).toBeInTheDocument();
    const day = seen.find((s) => s.get("group_by") === "day")!;
    expect(day.get("process_type")).toBe("Return");
    expect(day.get("tz_offset_min")).not.toBeNull();
    const from = new Date(day.get("date_from")!);
    const to = new Date(day.get("date_to")!);
    expect(Math.round((to.getTime() - from.getTime()) / 86_400_000)).toBe(29);
  });
});

describe("AdminPage", () => {
  it("creates an operator from the Users tab", async () => {
    let created: Record<string, unknown> | null = null;
    server.use(
      me("admin"),
      http.get("/api/v1/admin/users", () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 200 }),
      ),
      http.get("/api/v1/admin/warehouses", () => HttpResponse.json([])),
      http.post("/api/v1/admin/users", async ({ request }) => {
        created = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: 9,
            ...created,
            is_active: true,
            created_at: "2026-10-01T00:00:00Z",
            last_login_at: null,
          },
          { status: 201 },
        );
      }),
    );
    const user = userEvent.setup();
    renderPage(<AdminPage />, { path: "/admin" });
    expect(await screen.findByRole("tab", { name: "Users", selected: true })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /New user/ }));
    await user.type(screen.getByLabelText("Email"), "new.op@vms.local");
    await user.type(screen.getByLabelText("Name"), "New Op");
    await user.type(screen.getByLabelText("Initial password"), "operator-pass-1");
    // jsdom has no showModal(), so the dialog stays out of the accessibility tree.
    await user.click(screen.getByRole("button", { name: "Create user", hidden: true }));
    await waitFor(() => expect(created).not.toBeNull());
    expect(created).toEqual({
      email: "new.op@vms.local",
      name: "New Op",
      password: "operator-pass-1",
      role: "operator",
      warehouse_id: null,
    });
  });

  it("switches tabs with the arrow keys", async () => {
    server.use(
      me("admin"),
      http.get("/api/v1/admin/users", () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 200 }),
      ),
      http.get("/api/v1/admin/warehouses", () => HttpResponse.json([])),
      http.get("/api/v1/stations", () => HttpResponse.json([])),
    );
    const user = userEvent.setup();
    renderPage(<AdminPage />, { path: "/admin" });
    await user.click(await screen.findByRole("tab", { name: "Users" }));
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Warehouses & Stations" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(await screen.findByText(/No warehouses yet/)).toBeInTheDocument();
  });
});
