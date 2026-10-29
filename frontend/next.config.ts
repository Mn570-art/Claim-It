import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "*.trycloudflare.com"],
  async rewrites() {
    // Used by `next dev` only. On Vercel, vercel.json routes /api and /health.
    const api = process.env.API_PROXY_TARGET || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8741";
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/health", destination: `${api}/health` },
    ];
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
