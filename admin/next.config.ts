import type { NextConfig } from "next";

type NextConfigWithCompiler = NextConfig & {
  cacheComponents?: boolean;
  reactCompiler?: boolean;
};

const config: NextConfigWithCompiler = {
  experimental: {},
  cacheComponents: true,
  reactCompiler: true,
};

export default config;
