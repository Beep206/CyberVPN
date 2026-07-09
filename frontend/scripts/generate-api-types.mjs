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
const OPENAPI_TYPESCRIPT_CLI = resolve(
  ROOT,
  "..",
  "node_modules",
  "openapi-typescript",
  "bin",
  "cli.js",
);
const RETRYABLE_WRITE_ERROR_CODES = new Set(["EBUSY", "EACCES", "EPERM", "UNKNOWN"]);
const REQUIRED_MARKERS = [
  "get_metadata_api_v1_monitoring_metadata_get",
  "get_recap_api_v1_monitoring_recap_get",
  "node_version?: string | null;",
  "active_plugin_uuid?: string | null;",
];

function sleepSync(milliseconds) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, milliseconds);
}

function writeGeneratedFile(filePath, content) {
  let lastError;

  for (let attempt = 0; attempt < 6; attempt += 1) {
    try {
      writeFileSync(filePath, content, "utf-8");
      return;
    } catch (error) {
      lastError = error;
      if (!RETRYABLE_WRITE_ERROR_CODES.has(error?.code)) {
        throw error;
      }

      // Windows can briefly keep the just-generated file locked after the CLI exits.
      sleepSync(75 * (attempt + 1));
    }
  }

  throw lastError;
}

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

// Run the lockfile-backed openapi-typescript CLI using execFileSync (no shell injection risk)
try {
  execFileSync(process.execPath, [OPENAPI_TYPESCRIPT_CLI, OPENAPI_SPEC, "-o", OUTPUT_FILE], {
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

writeGeneratedFile(OUTPUT_FILE, generatedOutput);
