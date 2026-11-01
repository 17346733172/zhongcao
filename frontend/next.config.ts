import type { NextConfig } from "next";
const backend = (process.env.BACKEND_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const nextConfig: NextConfig = {
  devIndicators: false,
  // Local embedding model cold starts may exceed the default 30s proxy limit.
  experimental: { proxyTimeout: 190000 },
  reactStrictMode: true,
  async rewrites() { return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }]; },
};
export default nextConfig;
