// @vitest-environment node

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const OPENAPI_PATH = resolve(process.cwd(), '..', 'backend', 'docs', 'api', 'openapi.json');
const LEGACY_CHECKOUT_PATHS = [
  '/api/v1/payments/checkout/commit',
  '/api/v1/payments/checkout',
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function expectRecord(value: unknown): Record<string, unknown> {
  expect(isRecord(value)).toBe(true);
  return value as Record<string, unknown>;
}

function getPostOperation(path: string): Record<string, unknown> {
  const spec = expectRecord(JSON.parse(readFileSync(OPENAPI_PATH, 'utf8')) as unknown);
  const paths = expectRecord(spec.paths);
  const pathItem = expectRecord(paths[path]);
  return expectRecord(pathItem.post);
}

describe('legacy checkout OpenAPI contract', () => {
  it.each(LEGACY_CHECKOUT_PATHS)('%s is deprecated and fail-closed in generated artifacts', (path) => {
    const operation = getPostOperation(path);
    const responses = expectRecord(operation.responses);
    const parameters = operation.parameters;

    expect(operation.deprecated).toBe(true);
    expect(responses).toHaveProperty('410');
    expect(Array.isArray(parameters)).toBe(true);

    const idempotencyHeader = (parameters as unknown[])
      .filter(isRecord)
      .find((parameter) => parameter.name === 'Idempotency-Key' && parameter.in === 'header');

    expect(idempotencyHeader).toMatchObject({
      name: 'Idempotency-Key',
      in: 'header',
      required: true,
    });
    expect(expectRecord(idempotencyHeader?.schema)).toMatchObject({
      minLength: 1,
      maxLength: 120,
    });
  });
});
