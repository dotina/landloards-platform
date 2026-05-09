/** Environment configuration accessible from both server + client. */
const apiBaseResolved =
  process.env.NEXT_PUBLIC_API_BASE ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "/api";

export const env = {
  apiBase: apiBaseResolved,
  /** Set at build time (`NEXT_PUBLIC_AUTH_DEBUG`). Rebuild frontend after toggling. */
  authDebug: process.env.NEXT_PUBLIC_AUTH_DEBUG === "true",
} as const;
