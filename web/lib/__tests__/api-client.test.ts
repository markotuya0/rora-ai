import { ApiError, postQuery, approveAction } from "@/lib/api-client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("api-client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("maps the standard error envelope onto ApiError", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(400, {
        error: { code: "UNSAFE_SQL", message: "Unsafe SQL rejected", details: [], requestId: "req-abc", timestamp: "t" },
      }),
    );

    const err = await postQuery("drop everything").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ code: "UNSAFE_SQL", message: "Unsafe SQL rejected", requestId: "req-abc" });
  });

  it("falls back to HTTP status when the body is not an envelope", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("<html>bad gateway</html>", { status: 502 }));

    await expect(postQuery("hi")).rejects.toMatchObject({ code: "UNKNOWN", message: "HTTP 502" });
  });

  it("reports a network failure as NETWORK_ERROR", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(postQuery("hi")).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });

  it("reports an aborted request as CANCELLED", async () => {
    const controller = new AbortController();
    vi.mocked(fetch).mockImplementationOnce(() => {
      controller.abort();
      return Promise.reject(new DOMException("aborted", "AbortError"));
    });

    await expect(postQuery("hi", controller.signal)).rejects.toMatchObject({ code: "CANCELLED" });
  });

  it("posts approval decisions to the v1 approve endpoint", async () => {
    const payload = { status: "recorded", decision: "approve", request_id: "req-1", action_key: "cs_tags", actor: "unknown" };
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(200, payload));

    await expect(approveAction({ request_id: "req-1", action_key: "cs_tags", decision: "approve" })).resolves.toEqual(payload);
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/actions\/approve$/);
    expect(JSON.parse(String(init?.body))).toEqual({ request_id: "req-1", action_key: "cs_tags", decision: "approve" });
  });
});
