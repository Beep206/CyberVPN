import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";
import { withSentryConfig } from "@sentry/nextjs";

const CONFIG_DIR = dirname(fileURLToPath(import.meta.url));
const WORKSPACE_ROOT = dirname(CONFIG_DIR);
const ADMIN_PUBLIC_ORIGIN = "admin.cyber-vpn.net";
const ADMIN_LOCAL_ORIGINS = [
  "localhost",
  "127.0.0.1",
  "localhost:3001",
  "127.0.0.1:3001",
];
const publicSentryRelease =
  process.env.NEXT_PUBLIC_SENTRY_RELEASE?.trim() ||
  process.env.GITHUB_SHA?.trim() ||
  process.env.VERCEL_GIT_COMMIT_SHA?.trim() ||
  "cybervpn-admin-local";
const sentryAuthToken = process.env.SENTRY_AUTH_TOKEN?.trim();
const sentryOrg = process.env.SENTRY_ORG?.trim();
const sentryProject = process.env.SENTRY_PROJECT?.trim();
const configuredBuildCpus = Number.parseInt(process.env.NEXT_BUILD_CPUS ?? "", 10);
const buildWorkerCount =
  Number.isFinite(configuredBuildCpus) && configuredBuildCpus > 0
    ? configuredBuildCpus
    : 4;

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
    cpus: buildWorkerCount,
    staticGenerationRetryCount: 1,
    staticGenerationMaxConcurrency: Math.min(buildWorkerCount, 4),
    staticGenerationMinPagesPerWorker: 200,
    serverActions: {
      allowedOrigins: [ADMIN_PUBLIC_ORIGIN],
    },
  },
  allowedDevOrigins: [ADMIN_PUBLIC_ORIGIN, ...ADMIN_LOCAL_ORIGINS],
  cacheComponents: true,
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  reactCompiler: true,
  skipTrailingSlashRedirect: true,
  // Next 16/Turbopack must resolve the hoisted Next package from the monorepo root in CI.
  turbopack: {
    root: WORKSPACE_ROOT,
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
