// @vitest-environment node

import { describe, expect, it } from 'vitest';
import {
  MUTATION_GC_TIME_MS,
  QUERY_GC_TIME_MS,
  QUERY_STALE_TIME_MS,
  exponentialRetryDelay,
  queryClientDefaultOptions,
  shouldRetryQuery,
} from '../query-client-policy';

describe('partner query client policy', () => {
  it('pins bounded query retries and non-retrying mutations for partner operations', () => {
    expect(queryClientDefaultOptions.queries?.staleTime).toBe(QUERY_STALE_TIME_MS);
    expect(queryClientDefaultOptions.queries?.gcTime).toBe(QUERY_GC_TIME_MS);
    expect(queryClientDefaultOptions.mutations?.retry).toBe(false);
    expect(queryClientDefaultOptions.mutations?.gcTime).toBe(MUTATION_GC_TIME_MS);

    expect(shouldRetryQuery(0, { response: { status: 401 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 403 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 404 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 429 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 503 } })).toBe(true);
    expect(shouldRetryQuery(1, { status: 500 })).toBe(true);
    expect(shouldRetryQuery(2, { status: 500 })).toBe(false);
    expect(exponentialRetryDelay(0)).toBe(1_000);
    expect(exponentialRetryDelay(4)).toBe(10_000);
  });
});
