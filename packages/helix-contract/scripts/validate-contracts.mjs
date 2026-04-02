import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const packageRoot = path.resolve(__dirname, "..");

const ajv = new Ajv2020({
  allErrors: true,
  strict: false
});
addFormats(ajv);

const fixtures = [
  ["manifest.schema.json", "manifest.example.json"],
  ["node-assignment.schema.json", "node-assignment.example.json"],
  ["node-heartbeat.schema.json", "node-heartbeat.example.json"],
  ["client-capabilities.schema.json", "client-capabilities.example.json"],
  ["transport-profile.schema.json", "transport-profile.example.json"],
  ["benchmark-report.schema.json", "benchmark-report.example.json"],
  ["rollout-state.schema.json", "rollout-state.example.json"]
];

async function loadJson(filePath) {
  const raw = await readFile(filePath, "utf8");
  return JSON.parse(raw);
}

let passed = 0;
let failed = 0;

for (const [schemaFile, exampleFile] of fixtures) {
  const schema = await loadJson(path.join(packageRoot, "schema", schemaFile));
  const example = await loadJson(path.join(packageRoot, "examples", exampleFile));
  const validate = ajv.compile(schema);
  const ok = validate(example);

  if (ok) {
    console.log(`PASS ${exampleFile} -> ${schemaFile}`);
    passed += 1;
    continue;
  }

  console.error(`FAIL ${exampleFile} -> ${schemaFile}`);
  for (const error of validate.errors ?? []) {
    console.error(`  - ${error.instancePath || "/"} ${error.message}`);
  }
  failed += 1;
}

if (failed > 0) {
  console.error(`\nContract validation failed: ${passed} passed, ${failed} failed.`);
  process.exit(1);
}

console.log(`\nContract validation passed: ${passed} passed, ${failed} failed.`);
