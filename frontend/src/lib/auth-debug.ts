import { CSRF_COOKIE_NAME } from "./csrf";
import { env } from "./env";

const PREFIX = "[landloads:auth]";

/** Visible (non-httpOnly) session-related cookie probe — does not imply access JWT is stored. */
export function hasVisibleCsrfCookie(): boolean {
  if (typeof document === "undefined") return false;
  return new RegExp(`(?:^|;\\s*)${CSRF_COOKIE_NAME}=`).test(document.cookie);
}

/** Opt-in noisy logs (`NEXT_PUBLIC_AUTH_DEBUG=true` at Next build time). */
export function authDebug(message: string, payload?: Record<string, unknown>): void {
  if (!env.authDebug || typeof window === "undefined") return;
  if (payload !== undefined) {
    console.info(PREFIX, message, payload);
  } else {
    console.info(PREFIX, message);
  }
}
