#!/usr/bin/env node
/**
 * Generate TypeScript types from the backend OpenAPI specification.
 *
 * Usage:
 *   node scripts/generate-api-types.mjs
 *   npm run generate:api-types
 *
 * Source:  ../backend/docs/api/openapi.json (OpenAPI 3.1.0)
 * Output:  src/lib/api/generated/types.ts
 *
 * The generated types can be imported as:
 *   import type { paths, components, operations } from '@/lib/api/generated/types';
 */

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");

const OPENAPI_SPEC = resolve(ROOT, "..", "backend", "docs", "api", "openapi.json");
const OUTPUT_FILE = resolve(ROOT, "src", "lib", "api", "generated", "types.ts");
const REQUIRED_MARKERS = [
  "get_metadata_api_v1_monitoring_metadata_get",
  "get_recap_api_v1_monitoring_recap_get",
  "node_version?: string | null;",
  "active_plugin_uuid?: string | null;",
];

// Validate the OpenAPI spec exists
if (!existsSync(OPENAPI_SPEC)) {
  console.error(`OpenAPI spec not found at: ${OPENAPI_SPEC}`);
  console.error("Make sure the backend OpenAPI spec has been generated.");
  process.exit(1);
}

// Ensure the output directory exists
const outputDir = dirname(OUTPUT_FILE);
if (!existsSync(outputDir)) {
  mkdirSync(outputDir, { recursive: true });
}

// Run openapi-typescript CLI using execFileSync (no shell injection risk)
try {
  execFileSync("npx", ["openapi-typescript", OPENAPI_SPEC, "-o", OUTPUT_FILE], {
    cwd: ROOT,
    stdio: "inherit",
  });
} catch {
  console.error("Failed to generate API types.");
  process.exit(1);
}

// Prepend project-specific comment to the generated file
const HEADER = `/* eslint-disable */
/**
 * AUTO-GENERATED -- DO NOT EDIT
 *
 * Source:     backend/docs/api/openapi.json (OpenAPI 3.1.0)
 * Generator:  openapi-typescript v7
 * Regenerate: npm run generate:api-types
 */

`;

const content = readFileSync(OUTPUT_FILE, "utf-8");
const generatedOutput = HEADER + content;

for (const marker of REQUIRED_MARKERS) {
  if (!generatedOutput.includes(marker)) {
    console.error(`Generated API types are missing required Remnawave marker: ${marker}`);
    process.exit(1);
  }
}

writeFileSync(OUTPUT_FILE, generatedOutput, "utf-8");
