/** Hard-navigation helper.
 *
 * After authenticating we deliberately bypass Next.js's soft client router so the
 * browser issues a fresh top-level GET that includes the just-set session cookies
 * and any RSC caches are dropped. Centralising this lets tests stub a single export
 * (jsdom's `window.location.assign` throws "not implemented").
 */
export function hardNavigate(href: string): void {
  if (typeof window === "undefined") return;
  window.location.assign(href);
}
