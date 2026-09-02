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
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");

const OPENAPI_SPEC = resolve(
  ROOT,
  "..",
  "backend",
  "docs",
  "api",
  "openapi.json",
);
const OUTPUT_FILE = resolve(ROOT, "src", "lib", "api", "generated", "types.ts");
const OPENAPI_TYPESCRIPT_CLI = resolve(
  ROOT,
  "..",
  "node_modules",
  "openapi-typescript",
  "bin",
  "cli.js",
);
const RETRYABLE_WRITE_ERROR_CODES = new Set([
  "EBUSY",
  "EACCES",
  "EPERM",
  "UNKNOWN",
]);

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

function generateTypes() {
  const temporaryDirectory = mkdtempSync(join(tmpdir(), "cybervpn-openapi-"));
  const generatedFile = join(temporaryDirectory, "types.ts");

  try {
    // Generate away from the watched workspace. Windows indexers and language
    // servers may briefly lock the committed target after a prior run.
    execFileSync(
      process.execPath,
      [OPENAPI_TYPESCRIPT_CLI, OPENAPI_SPEC, "-o", generatedFile],
      {
        cwd: ROOT,
        stdio: "inherit",
      },
    );
    const content = readFileSync(generatedFile, "utf-8");
    writeGeneratedFile(OUTPUT_FILE, HEADER + content);
  } finally {
    rmSync(temporaryDirectory, { recursive: true, force: true });
  }
}

try {
  generateTypes();
} catch {
  console.error("Failed to generate API types.");
  process.exit(1);
}
