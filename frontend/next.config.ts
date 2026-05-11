import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";
import { withSentryConfig } from "@sentry/nextjs";

const CONFIG_DIR = dirname(fileURLToPath(import.meta.url));
const publicSentryRelease =
  process.env.NEXT_PUBLIC_SENTRY_RELEASE?.trim() ||
  process.env.GITHUB_SHA?.trim() ||
  process.env.VERCEL_GIT_COMMIT_SHA?.trim() ||
  "cybervpn-frontend-local";
const sentryAuthToken = process.env.SENTRY_AUTH_TOKEN?.trim();
const sentryOrg = process.env.SENTRY_ORG?.trim();
const sentryProject = process.env.SENTRY_PROJECT?.trim();
const FRONTEND_PRIMARY_ORIGIN = "cyber-vpn.net";
const FRONTEND_WWW_ORIGIN = "www.cyber-vpn.net";
const FRONTEND_LOCAL_ORIGINS = ["localhost:3000", "127.0.0.1:3000"];
const apiInternalOrigin = (
  process.env.API_INTERNAL_ORIGIN?.trim() ||
  process.env.API_URL?.trim() ||
  "http://localhost:8000"
).replace(/\/$/, "");

type NextConfigWithCompiler = NextConfig & {
  cacheComponents?: boolean;
  reactCompiler?: boolean;
  allowedDevOrigins?: string[];
};

// SEC-03: Content-Security-Policy in Report-Only mode.
// Allows: WebGL (Three.js), inline styles (Tailwind), Sentry, Google Fonts, Telegram.
const cspDirectives = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://telegram.org https://*.sentry.io",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "img-src 'self' data: blob: https:",
  "font-src 'self' https://fonts.gstatic.com",
  "connect-src 'self' https://*.sentry.io https://*.ingest.sentry.io https://raw.githack.com https://raw.githubusercontent.com wss: ws:",
  "worker-src 'self' blob:",
  "frame-src 'self' https://oauth.telegram.org",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const config: NextConfigWithCompiler = {
  experimental: {
    globalNotFound: true,
    // Avoid WSL CPU/RAM spikes from Turbopack dev filesystem-cache compaction.
    turbopackFileSystemCacheForDev: false,
    serverActions: {
      allowedOrigins: [FRONTEND_PRIMARY_ORIGIN, FRONTEND_WWW_ORIGIN],
    },
  },
  allowedDevOrigins: [
    FRONTEND_PRIMARY_ORIGIN,
    FRONTEND_WWW_ORIGIN,
    ...FRONTEND_LOCAL_ORIGINS,
  ],
  cacheComponents: true,
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  reactCompiler: true,
  skipTrailingSlashRedirect: true,
  // Keep Turbopack scoped to the Next.js app so WSL does not watch the entire monorepo.
  turbopack: {
    root: CONFIG_DIR,
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy-Report-Only",
            value: cspDirectives,
          },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiInternalOrigin}/api/v1/:path*`,
      },
    ];
  },
};

const withNextIntl = createNextIntlPlugin();

export default withSentryConfig(withNextIntl(config), {
  // Suppress source map upload warnings when SENTRY_AUTH_TOKEN is not set
  silent: !sentryAuthToken,

  ...(sentryAuthToken ? { authToken: sentryAuthToken } : {}),
  ...(sentryOrg ? { org: sentryOrg } : {}),
  ...(sentryProject ? { project: sentryProject } : {}),

  // Sentry injects the release into the browser bundle. Keep it explicitly public.
  release: {
    name: publicSentryRelease,
  },

  // Upload source maps for readable stack traces
  widenClientFileUpload: true,

});
