import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

type NextConfigWithCompiler = NextConfig & {
  cacheComponents?: boolean;
  reactCompiler?: boolean;
};

const config: NextConfigWithCompiler = {
  experimental: {},
  cacheComponents: true,
  reactCompiler: true,
};

const withNextIntl = createNextIntlPlugin();

export default withNextIntl(config);
