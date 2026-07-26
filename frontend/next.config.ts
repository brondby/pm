import type { NextConfig } from "next";

/**
 * Next.js configuration for static export.
 *
 * The MVP requires the frontend to be served as pure static files from the
 * FastAPI backend. In Next.js 16 the legacy `next export` command was removed;
 * instead we enable static export via the `output: 'export'` option.
 * This generates an `out/` directory containing `index.html` and all assets.
 */
const nextConfig: NextConfig = {
  // Enable static export so the build can be copied into the backend static folder.
  output: "export",
  // Optional but useful defaults for the MVP.
  reactStrictMode: true,
  // Ensure the base path is `/` (default) – no special routing needed.
  // Any additional Next.js options can be added here if required.
};

export default nextConfig;
