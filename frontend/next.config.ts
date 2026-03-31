import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";
import { withSentryConfig } from "@sentry/nextjs";

const CONFIG_DIR = dirname(fileURLToPath(import.meta.url));

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
    serverActions: {
      allowedOrigins: ["vpn.ozoxy.ru"],
    },
  },
  allowedDevOrigins: ["vpn.ozoxy.ru"],
  cacheComponents: true,
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  reactCompiler: true,
  skipTrailingSlashRedirect: true,
  turbopack: {
    root: join(CONFIG_DIR, '..'),
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
        destination: "http://localhost:8000/api/v1/:path*",
      },
    ];
  },
};

const withNextIntl = createNextIntlPlugin();

export default withSentryConfig(withNextIntl(config), {
  // Suppress source map upload warnings when SENTRY_AUTH_TOKEN is not set
  silent: !process.env.SENTRY_AUTH_TOKEN,

  // Upload source maps for readable stack traces
  widenClientFileUpload: true,

});
