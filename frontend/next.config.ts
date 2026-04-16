import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: ["10.0.0.251"],
  turbopack: {
    root: path.resolve(import.meta.dirname),
  },
  headers: async () => [
    {
      source: "/((?!_next/static|favicon.ico).*)",
      headers: [
        { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
      ],
    },
  ],
};

export default nextConfig;
