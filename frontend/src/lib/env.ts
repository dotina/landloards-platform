/** Environment configuration accessible from both server + client. */
export const env = {
  apiBase: process.env.NEXT_PUBLIC_API_BASE ?? "/api",
} as const;
