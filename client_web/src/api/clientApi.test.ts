import { afterEach, describe, expect, it, vi } from "vitest";

import { CLIENT_SESSION_INVALIDATED_EVENT, CLIENT_API_BASE, clientApi } from "./clientApi";

describe("clientApi", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends JSON headers and returns JSON payloads", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(clientApi("/auth/me", { headers: { "X-Test": "1" } })).resolves.toEqual({ ok: true });

    expect(fetchMock).toHaveBeenCalledWith(`${CLIENT_API_BASE}/auth/me`, {
      credentials: "include",
      headers: expect.any(Headers),
    });
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-Test")).toBe("1");
  });

  it("keeps provided content type and returns text or empty payloads", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("plain", { status: 200, headers: { "content-type": "text/plain" } }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(clientApi<string>("/plain", { headers: { "Content-Type": "text/plain" } })).resolves.toBe("plain");
    await expect(clientApi<null>("/empty")).resolves.toBeNull();

    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Content-Type")).toBe("text/plain");
  });

  it("throws response detail and dispatches session invalidation on 401", async () => {
    const listener = vi.fn();
    window.addEventListener(CLIENT_SESSION_INVALIDATED_EVENT, listener);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Session expired" }), {
          status: 401,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(clientApi("/auth/me")).rejects.toThrow("Session expired");

    expect(listener).toHaveBeenCalledOnce();
    expect(listener.mock.calls[0][0]).toMatchObject({ detail: "Session expired" });
    window.removeEventListener(CLIENT_SESSION_INVALIDATED_EVENT, listener);
  });

  it("does not dispatch session invalidation for credential 401 errors", async () => {
    const listener = vi.fn();
    window.addEventListener(CLIENT_SESSION_INVALIDATED_EVENT, listener);
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Invalid credentials" }), {
          status: 401,
          headers: { "content-type": "application/json" },
        }),
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ detail: "Invalid current password" }), {
            status: 401,
            headers: { "content-type": "application/json" },
          }),
        ),
    );

    await expect(clientApi("/auth/verify-password")).rejects.toThrow("Invalid credentials");
    await expect(clientApi("/auth/password")).rejects.toThrow("Invalid current password");

    expect(listener).not.toHaveBeenCalled();
    window.removeEventListener(CLIENT_SESSION_INVALIDATED_EVENT, listener);
  });

  it("falls back to status text when error payload cannot be read", async () => {
    const brokenResponse = {
      ok: false,
      status: 500,
      statusText: "Broken",
      text: vi.fn().mockRejectedValue(new Error("read failed")),
      headers: new Headers(),
    } as unknown as Response;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(brokenResponse));

    await expect(clientApi("/broken")).rejects.toThrow("Broken");
  });

  it("falls back for non-string detail and missing status text without invalidating the session", async () => {
    const listener = vi.fn();
    window.addEventListener(CLIENT_SESSION_INVALIDATED_EVENT, listener);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 42 }), {
          status: 400,
          statusText: "Bad Request",
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ message: "no detail" }), {
          status: 500,
          statusText: "",
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(clientApi("/bad-detail")).rejects.toThrow("Bad Request");
    await expect(clientApi("/default-error")).rejects.toThrow("Request failed");

    expect(listener).not.toHaveBeenCalled();
    window.removeEventListener(CLIENT_SESSION_INVALIDATED_EVENT, listener);
  });
});
