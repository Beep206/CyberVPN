import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // React Compiler (stable in 19, enabled via experimental flag in Next 15/16 if needed, or root prop)
    // The prompt says "reactCompiler: true" and "cacheComponents: true" in root object.
    // In Next.js 16 (simulated), these might be root properties.
    // I will try to put them in root as requested.
    // Use 'any' cast if TS complains about unknown properties in this simulated version.
  } as any,
};

// Extending with prompt specific properties
const config = {
  ...nextConfig,
  cacheComponents: true,
  reactCompiler: true,
};

export default config;
