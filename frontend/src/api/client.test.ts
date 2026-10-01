import { http, HttpResponse } from "msw";
import { z } from "zod";
import { getToken, setToken } from "@/auth/tokenStore";
import { server } from "@/test/server";
import { ApiError, request, setUnauthorizedHandler } from "./client";

const ok = z.object({ ok: z.boolean() });

describe("api client", () => {
  it("sends the bearer token and parses the response", async () => {
    setToken("tok");
    let auth: string | null = null;
    server.use(
      http.get("/api/v1/x", ({ request: r }) => {
        auth = r.headers.get("Authorization");
        return HttpResponse.json({ ok: true });
      }),
    );
    await expect(request("/api/v1/x", ok)).resolves.toEqual({ ok: true });
    expect(auth).toBe("Bearer tok");
  });

  it("on 401 drops the token and calls the logout handler", async () => {
    setToken("tok");
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    server.use(
      http.get("/api/v1/x", () =>
        HttpResponse.json({ detail: "Invalid or expired token." }, { status: 401 }),
      ),
    );
    await expect(request("/api/v1/x", ok)).rejects.toMatchObject({
      status: 401,
      message: "Invalid or expired token.",
    });
    expect(handler).toHaveBeenCalledOnce();
    expect(getToken()).toBeNull();
  });

  it("maps 429 to a friendly message and keeps `detail` for other errors", async () => {
    server.use(
      http.post("/api/v1/auth/login", () => HttpResponse.json({ detail: "x" }, { status: 429 })),
      http.get("/api/v1/x", () =>
        HttpResponse.json({ detail: "Not your video." }, { status: 403 }),
      ),
    );
    await expect(request("/api/v1/auth/login", ok, { method: "POST" })).rejects.toThrow(
      /Too many attempts/,
    );
    const err = await request("/api/v1/x", ok).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 403, message: "Not your video." });
  });

  it("rejects responses that break the schema, and network failures", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.get("/api/v1/x", () => HttpResponse.json({ ok: "yes" })));
    await expect(request("/api/v1/x", ok)).rejects.toThrow(/unexpected response/);
    server.use(http.get("/api/v1/x", () => HttpResponse.error()));
    await expect(request("/api/v1/x", ok)).rejects.toMatchObject({ status: 0 });
  });
});
