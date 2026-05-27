export const CLIENT_API_BASE = "/api/v1/client-web";
export const CLIENT_SESSION_INVALIDATED_EVENT = "cronolex-client-session-invalidated";

const SESSION_INVALIDATION_DETAILS = [
  "not authenticated",
  "session expired",
  "device or network changed",
] as const;
const AUTH_REQUEST_PREFIXES = [
  "/auth/start",
  "/auth/verify-password",
  "/auth/verify-otp",
  "/auth/magic",
] as const;

export async function clientApi<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${CLIENT_API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: jsonHeaders(options.headers)
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    if (shouldInvalidateSession(path, response.status, detail)) {
      window.dispatchEvent(new CustomEvent(CLIENT_SESSION_INVALIDATED_EVENT, { detail }));
    }
    throw new Error(detail);
  }
  return readResponsePayload<T>(response);
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const payload = await readResponsePayload<unknown>(response);
    if (payload && typeof payload === "object" && "detail" in payload) {
      const detail = (payload as { detail: unknown }).detail;
      if (typeof detail === "string" && detail) return detail;
    }
  } catch {
    // keep response fallback
  }
  return response.statusText || "Request failed";
}

async function readResponsePayload<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) return null as T;
  const contentType = response.headers.get("content-type");
  if (contentType?.toLowerCase().includes("application/json")) return JSON.parse(text) as T;
  return text as T;
}

function jsonHeaders(headers: HeadersInit | undefined): Headers {
  const merged = new Headers(headers);
  if (!merged.has("Content-Type")) merged.set("Content-Type", "application/json");
  return merged;
}

function shouldInvalidateSession(path: string, status: number, detail: string): boolean {
  const normalizedDetail = detail.toLowerCase();
  return (
    status === 401
    && !AUTH_REQUEST_PREFIXES.some((prefix) => path.startsWith(prefix))
    && SESSION_INVALIDATION_DETAILS.some((sessionDetail) => normalizedDetail.includes(sessionDetail))
  );
}
