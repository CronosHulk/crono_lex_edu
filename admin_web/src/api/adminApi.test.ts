import { afterEach, describe, expect, it, vi } from "vitest";
import { adminApi, ADMIN_API_BASE, SESSION_INVALIDATED_EVENT } from "./adminApi";

describe("adminApi", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends admin API requests with JSON headers and included credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(adminApi("/bootstrap", { method: "POST", body: JSON.stringify({ a: 1 }) })).resolves.toEqual({ ok: true });

    expect(fetchMock).toHaveBeenCalledWith(`${ADMIN_API_BASE}/bootstrap`, expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ a: 1 }),
      credentials: "include"
    }));
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("preserves caller headers while adding the default content type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await adminApi("/users", { headers: { "X-Trace": "abc" } });

    const headers = new Headers((fetchMock.mock.calls[0][1] as RequestInit).headers);
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-Trace")).toBe("abc");
  });

  it("lets callers override the content type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(textResponse("saved"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(adminApi("/upload", { headers: { "Content-Type": "text/plain" } })).resolves.toBe("saved");

    const headers = new Headers((fetchMock.mock.calls[0][1] as RequestInit).headers);
    expect(headers.get("Content-Type")).toBe("text/plain");
  });

  it("returns null for an empty successful response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    await expect(adminApi("/empty")).resolves.toBeNull();
  });

  it("throws JSON detail values for failed responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Bad request" }, { status: 400, statusText: "Bad" })));

    await expect(adminApi("/broken")).rejects.toThrow("Bad request");
  });

  it("throws object detail message values for failed responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({
      detail: { code: "topic_difficulty_conflict", message: "Selected grammar topic is above selected difficulty_band" },
    }, { status: 409, statusText: "Conflict" })));

    await expect(adminApi("/conflict")).rejects.toThrow("Selected grammar topic is above selected difficulty_band");
  });

  it("falls back to status text when JSON detail is missing", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ message: "No detail" }, { status: 500, statusText: "Server exploded" })));

    await expect(adminApi("/missing-detail")).rejects.toThrow("Server exploded");
  });

  it("falls back to status text when JSON detail is not a string or validation list", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: 123 }, { status: 422, statusText: "Invalid detail" })));

    await expect(adminApi("/numeric-detail")).rejects.toThrow("Invalid detail");

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "" }, { status: 422, statusText: "Empty detail" })));

    await expect(adminApi("/empty-detail")).rejects.toThrow("Empty detail");

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: { message: 123 } }, { status: 422, statusText: "Object detail" })));

    await expect(adminApi("/object-detail-without-message")).rejects.toThrow("Object detail");
  });

  it("formats FastAPI validation error details", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({
      detail: [
        { loc: ["body", "challenge_id"], msg: "Field required", type: "missing" },
        { loc: ["body", "otp"], msg: "String should have at least 6 characters", type: "string_too_short" },
      ]
    }, { status: 422, statusText: "" })));

    await expect(adminApi("/validation-error")).rejects.toThrow(
      "challenge_id: Field required; otp: String should have at least 6 characters"
    );
  });

  it("formats validation details without body locations and notes hidden extra errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({
      detail: [
        { loc: "otp", msg: "Malformed location", type: "value_error" },
        { loc: ["query", "page"], msg: "Input should be greater than 0", type: "greater_than" },
        { msg: "Payload is invalid", type: "value_error" },
        null,
      ]
    }, { status: 422, statusText: "" })));

    await expect(adminApi("/validation-error-with-extra")).rejects.toThrow(
      "Malformed location; query.page: Input should be greater than 0; Payload is invalid; +1 more"
    );
  });

  it("falls back to status text when validation details have no messages", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({
      detail: [null, { loc: ["body", "otp"], type: "missing" }]
    }, { status: 422, statusText: "Invalid payload" })));

    await expect(adminApi("/validation-error-without-message")).rejects.toThrow("Invalid payload");
  });

  it("falls back to status text when an error response body is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(textResponse("nope", { status: 500, statusText: "Plain error" })));

    await expect(adminApi("/plain-error")).rejects.toThrow("Plain error");
  });

  it("falls back to status text when an error response body is not valid JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{", {
      status: 500,
      statusText: "Invalid JSON",
      headers: { "Content-Type": "application/json" }
    })));

    await expect(adminApi("/invalid-json")).rejects.toThrow("Invalid JSON");
  });

  it("falls back to the default error text when invalid JSON has no status text", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{", {
      status: 500,
      statusText: "",
      headers: { "Content-Type": "application/json" }
    })));

    await expect(adminApi("/invalid-json-empty-status")).rejects.toThrow("Request failed");
  });

  it("falls back to the default error text when no detail or status text exists", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 500, statusText: "" })));

    await expect(adminApi("/empty-error")).rejects.toThrow("Request failed");
  });

  it("returns text responses without a content type", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(new TextEncoder().encode("plain"), { status: 200 })));

    await expect(adminApi("/plain")).resolves.toBe("plain");
  });

  it("dispatches a session invalidation event for protected 401 errors", async () => {
    const listener = vi.fn();
    window.addEventListener(SESSION_INVALIDATED_EVENT, listener);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(
      { detail: "Not authenticated" },
      { status: 401, statusText: "Unauthorized" }
    )));

    await expect(adminApi("/me")).rejects.toThrow("Not authenticated");

    expect(listener).toHaveBeenCalledTimes(1);
    expect((listener.mock.calls[0][0] as CustomEvent<string>).detail).toBe("Not authenticated");
    window.removeEventListener(SESSION_INVALIDATED_EVENT, listener);
  });

  it("does not dispatch a session invalidation event for credential 401 errors", async () => {
    const listener = vi.fn();
    window.addEventListener(SESSION_INVALIDATED_EVENT, listener);
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(jsonResponse(
      { detail: "Invalid credentials" },
      { status: 401, statusText: "Unauthorized" }
      ))
      .mockResolvedValueOnce(jsonResponse(
        { detail: "Invalid current password" },
        { status: 401, statusText: "Unauthorized" }
      )));

    await expect(adminApi("/auth/verify-password")).rejects.toThrow("Invalid credentials");
    await expect(adminApi("/auth/password")).rejects.toThrow("Invalid current password");

    expect(listener).not.toHaveBeenCalled();
    window.removeEventListener(SESSION_INVALIDATED_EVENT, listener);
  });
});

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init
  });
}

function textResponse(body: string, init: ResponseInit = {}): Response {
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/plain" },
    ...init
  });
}
