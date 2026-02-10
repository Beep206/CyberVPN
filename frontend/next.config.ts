import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";
import { withSentryConfig } from "@sentry/nextjs";

type NextConfigWithCompiler = NextConfig & {
  cacheComponents?: boolean;
  reactCompiler?: boolean;
};

const config: NextConfigWithCompiler = {
  experimental: {},
  cacheComponents: true,
  reactCompiler: true,
  trailingSlash: true,
};

const withNextIntl = createNextIntlPlugin();

export default withSentryConfig(withNextIntl(config), {
  // Suppress source map upload warnings when SENTRY_AUTH_TOKEN is not set
  silent: !process.env.SENTRY_AUTH_TOKEN,

  // Upload source maps for readable stack traces
  widenClientFileUpload: true,

  // Automatically tree-shake unused Sentry code
  disableLogger: true,
});
