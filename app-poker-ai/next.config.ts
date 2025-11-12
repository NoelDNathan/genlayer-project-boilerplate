import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export', // Static export for GitHub Pages
  images: {
    unoptimized: true, // Required for GitHub Pages
  },
  // Remove trailing slashes for cleaner URLs
  trailingSlash: false,
};

export default nextConfig;

