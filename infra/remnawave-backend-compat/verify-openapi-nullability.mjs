#!/usr/bin/env node
import { readFileSync } from 'node:fs';

const openApiPath = process.argv[2] ?? '/opt/app/openapi.json';
const document = JSON.parse(readFileSync(openApiPath, 'utf8'));
const arrayTypePaths = [];
let anyOfCount = 0;

function walk(value, path) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => walk(item, `${path}[${index}]`));
    return;
  }
  if (value === null || typeof value !== 'object') {
    return;
  }
  if (Array.isArray(value.type)) {
    arrayTypePaths.push(`${path}/type`);
  }
  if (Array.isArray(value.anyOf)) {
    anyOfCount += 1;
  }
  for (const [key, child] of Object.entries(value)) {
    walk(child, `${path}/${key}`);
  }
}

walk(document, '');
if (arrayTypePaths.length > 0) {
  console.error(
    `Remnawave OpenAPI contains forbidden array-valued type fields: ${arrayTypePaths
      .slice(0, 10)
      .join(', ')}`,
  );
  process.exit(1);
}
if (anyOfCount === 0) {
  console.error('Remnawave OpenAPI contains no anyOf schemas; nullable-union patch may be absent.');
  process.exit(1);
}

console.log(
  `Verified Remnawave OpenAPI nullability: 0 array-valued type fields, ${anyOfCount} anyOf schemas.`,
);
