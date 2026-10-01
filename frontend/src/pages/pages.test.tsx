import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { detail, video } from "@/test/fixtures";
import { renderPage } from "@/test/render";
import { server } from "@/test/server";
import { VideoDetailPage } from "./VideoDetailPage";
import { VideosPage } from "./VideosPage";

const me = (role: string) =>
  http.get("/api/v1/auth/me", () =>
    HttpResponse.json({
      id: 2,
      email: "o@vms.local",
      name: "Ravi K.",
      role,
      warehouse_id: null,
      is_active: true,
      created_at: "2026-10-01T00:00:00Z",
      last_login_at: null,
    }),
  );

describe("VideosPage", () => {
  it("renders rows from the API and sends URL filters as query params", async () => {
    let seen = new URLSearchParams();
    server.use(
      me("operator"),
      http.get("/api/v1/videos", ({ request }) => {
        seen = new URL(request.url).searchParams;
        return HttpResponse.json({ items: [video()], total: 1, page: 1, page_size: 25 });
      }),
    );
    renderPage(<VideosPage />, { path: "/videos", url: "/videos?status=pass&q=AWB1" });
    const row = await screen.findByRole("row", { name: /Open ret_blr01_0931.mp4/ });
    expect(within(row).getByText("88")).toBeInTheDocument();
    expect(within(row).getByText("Pass")).toBeInTheDocument();
    expect(screen.getByText("Showing 1–1 of 1")).toBeInTheDocument();
    expect(seen.get("status")).toBe("pass");
    expect(seen.get("q")).toBe("AWB1");
  });

  it("shows an error with Retry", async () => {
    server.use(
      me("operator"),
      http.get("/api/v1/videos", () => HttpResponse.json({ detail: "Boom." }, { status: 500 })),
    );
    renderPage(<VideosPage />, { path: "/videos" });
    expect(await screen.findByText("Boom.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

describe("VideoDetailPage", () => {
  const routes = (role: string) => [
    me(role),
    http.get("/api/v1/videos/1", () => HttpResponse.json(detail())),
    http.get("/api/v1/rubrics", () => HttpResponse.json([])),
    http.get("/api/v1/evidence/31", () => new HttpResponse(null, { status: 404 })),
    http.get("/api/v1/videos/1/stream", () => new HttpResponse(null, { status: 404 })),
  ];

  it("shows verdict, steps and evidence markers; operators get no Re-analyze", async () => {
    server.use(...routes("operator"));
    renderPage(<VideoDetailPage />, { path: "/videos/:id", url: "/videos/1" });
    expect(await screen.findByText("Accepted")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Shipping Label & Barcode" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Jump to 0:03: step 1/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Re-analyze/ })).not.toBeInTheDocument();
  });

  it("shows Re-analyze to reviewers", async () => {
    server.use(...routes("reviewer"));
    renderPage(<VideoDetailPage />, { path: "/videos/:id", url: "/videos/1" });
    expect(await screen.findByRole("button", { name: /Re-analyze/ })).toBeInTheDocument();
  });
});
