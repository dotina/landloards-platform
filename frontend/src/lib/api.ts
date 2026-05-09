/** Thin fetch wrapper that:
 *  - Sends and accepts cookies (auth is JWT-cookie based).
 *  - Auto-injects the CSRF double-submit header on mutating requests.
 *  - Throws ApiError on non-2xx responses with the JSON body when present. */
import { env } from "./env";

/** Must match backend `CSRF_COOKIE` (`app.auth.deps`). */
export const CSRF_COOKIE_NAME = "ll_csrf";

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = "ApiError";
  }
}

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.match(
    new RegExp("(?:^|;\\s*)" + name + "=([^;]+)")
  );
  return match ? decodeURIComponent(match[1]) : undefined;
}

type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export interface ApiOpts {
  method?: Method;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export async function api<T = unknown>(
  path: string,
  opts: ApiOpts = {}
): Promise<T> {
  const method: Method = opts.method ?? "GET";
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(opts.headers ?? {}),
  };

  let body: BodyInit | undefined;
  if (opts.body instanceof FormData) {
    body = opts.body;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  if (method !== "GET") {
    const csrf = readCookie(CSRF_COOKIE_NAME);
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  const res = await fetch(env.apiBase + path, {
    method,
    headers,
    body,
    credentials: "include",
    signal: opts.signal,
  });

  const ct = res.headers.get("content-type") ?? "";
  let payload: unknown = null;
  if (ct.includes("application/json")) {
    payload = await res.json().catch(() => null);
  } else if (res.status !== 204) {
    payload = await res.text().catch(() => null);
  }

  if (!res.ok) {
    const detail =
      typeof payload === "object" && payload && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : res.statusText;
    throw new ApiError(res.status, detail, payload);
  }
  return payload as T;
}
