/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // typedRoutes is intentionally OFF: Phases 14–15 will iterate on routes a
  // lot, and the typed-route compile errors slow down moves between
  // PR-sized commits. Flip back on after Phase 15 when the route map is
  // stable.
  experimental: {
    typedRoutes: false,
  },
};

export default nextConfig;
