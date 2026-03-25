import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const AUTH_SERVICE_URL =
  process.env.AUTH_SERVICE_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ??
  "http://localhost:4000";

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: "/api/auth/:path*",
        destination: `${AUTH_SERVICE_URL}/api/auth/:path*`,
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com',
        port: '',
        pathname: '/a/**',
      }
    ],
  },
};

export default withSentryConfig(nextConfig, {
  // Sentry Webpack Plugin Options
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,

  // Only upload source maps in production builds
  silent: true,

  // Automatically tree-shake Sentry logger statements in production
  widenClientFileUpload: true,

  // tunnelRoute disabled — causes React 19 script tag warning
  // tunnelRoute: "/monitoring",

  // Disable source map upload in development
  ...(process.env.NODE_ENV !== 'production' && {
    dryRun: true,
  }),
});