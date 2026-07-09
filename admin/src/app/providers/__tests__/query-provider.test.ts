// @vitest-environment node

import fs from 'fs/promises';
import path from 'path';
import { describe, expect, it } from 'vitest';
import {
  MUTATION_GC_TIME_MS,
  QUERY_GC_TIME_MS,
  QUERY_STALE_TIME_MS,
  exponentialRetryDelay,
  queryClientDefaultOptions,
  shouldRetryQuery,
} from '../query-client-policy';

const PROVIDER_PATH = path.resolve(__dirname, '../query-provider.tsx');

async function readQueryProvider() {
  return fs.readFile(PROVIDER_PATH, 'utf-8');
}

describe('QueryProvider source contract', () => {
  it('keeps React Query Devtools behind explicit public opt-in', async () => {
    const source = await readQueryProvider();

    expect(source).toContain('NEXT_PUBLIC_ENABLE_REACT_QUERY_DEVTOOLS');
    expect(source).toContain("process.env.NODE_ENV !== 'production'");
    expect(source).toContain(
      "process.env.NEXT_PUBLIC_ENABLE_REACT_QUERY_DEVTOOLS === 'true'",
    );
    expect(source).toContain('isReactQueryDevtoolsEnabled');
    expect(source).toContain('queryClientDefaultOptions');
    expect(source).toContain('<QueryClientProvider client={queryClient}>');
    expect(source).toContain('{children}');
  });

  it('pins bounded query retries and non-retrying mutations for admin operations', () => {
    expect(queryClientDefaultOptions.queries?.staleTime).toBe(QUERY_STALE_TIME_MS);
    expect(queryClientDefaultOptions.queries?.gcTime).toBe(QUERY_GC_TIME_MS);
    expect(queryClientDefaultOptions.mutations?.retry).toBe(false);
    expect(queryClientDefaultOptions.mutations?.gcTime).toBe(MUTATION_GC_TIME_MS);

    expect(shouldRetryQuery(0, { response: { status: 401 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 403 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 404 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 429 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 503 } })).toBe(true);
    expect(shouldRetryQuery(1, { statusCode: 502 })).toBe(true);
    expect(shouldRetryQuery(2, { statusCode: 502 })).toBe(false);
    expect(exponentialRetryDelay(0)).toBe(1_000);
    expect(exponentialRetryDelay(4)).toBe(10_000);
  });
});
