import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  output: 'standalone',
  allowedDevOrigins: ['dev.phpxcoder.in'],
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