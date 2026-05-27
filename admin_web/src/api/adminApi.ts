export const ADMIN_API_BASE = "/api/v1/admin";
export const SESSION_INVALIDATED_EVENT = "cronolex-session-invalidated";

const DEFAULT_ERROR_DETAIL = "Request failed";
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

export async function adminApi<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${ADMIN_API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: jsonHeaders(options.headers)
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    if (shouldInvalidateSession(path, response.status, detail)) {
      window.dispatchEvent(new CustomEvent(SESSION_INVALIDATED_EVENT, { detail }));
    }
    throw new Error(detail);
  }

  return readResponsePayload<T>(response);
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const payload = await readResponsePayload<unknown>(response);
    return detailFromPayload(payload) || response.statusText || DEFAULT_ERROR_DETAIL;
  } catch {
    return response.statusText || DEFAULT_ERROR_DETAIL;
  }
}

async function readResponsePayload<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) return null as T;

  const contentType = response.headers.get("content-type");
  if (contentType === null) return text as T;
  if (contentType.toLowerCase().includes("application/json")) {
    return JSON.parse(text) as T;
  }

  return text as T;
}

function detailFromPayload(payload: unknown): string | null {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) return null;
  const detail = (payload as { detail: unknown }).detail;
  if (typeof detail === "string" && detail) return detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string" && message) return message;
  }
  return detailFromValidationErrors(detail);
}

function detailFromValidationErrors(detail: unknown): string | null {
  if (!Array.isArray(detail) || detail.length === 0) return null;
  const messages = detail
    .slice(0, 3)
    .map((item) => validationErrorMessage(item))
    .filter((message): message is string => Boolean(message));
  if (messages.length === 0) return null;
  const remaining = detail.length - messages.length;
  return remaining > 0 ? `${messages.join("; ")}; +${remaining} more` : messages.join("; ");
}

function validationErrorMessage(item: unknown): string | null {
  if (!item || typeof item !== "object") return null;
  const record = item as { loc?: unknown; msg?: unknown };
  const msg = typeof record.msg === "string" ? record.msg : "";
  if (!msg) return null;
  const loc = Array.isArray(record.loc)
    ? record.loc.filter((part) => part !== "body").map(String).join(".")
    : "";
  return loc ? `${loc}: ${msg}` : msg;
}

function shouldInvalidateSession(path: string, status: number, detail: string): boolean {
  const normalizedDetail = detail.toLowerCase();
  return (
    status === 401
    && !AUTH_REQUEST_PREFIXES.some((prefix) => path.startsWith(prefix))
    && SESSION_INVALIDATION_DETAILS.some((sessionDetail) => normalizedDetail.includes(sessionDetail))
  );
}

function jsonHeaders(headers: HeadersInit | undefined): Headers {
  const merged = new Headers(headers);
  if (!merged.has("Content-Type")) {
    merged.set("Content-Type", "application/json");
  }
  return merged;
}
