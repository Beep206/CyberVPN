import type { DefaultOptions } from '@tanstack/react-query';

export const QUERY_STALE_TIME_MS = 60_000;
export const QUERY_GC_TIME_MS = 5 * 60_000;
export const MUTATION_GC_TIME_MS = 60_000;
export const MAX_QUERY_RETRY_ATTEMPTS = 2;
export const MAX_QUERY_RETRY_DELAY_MS = 10_000;

type HttpErrorShape = {
  response?: {
    status?: unknown;
  };
  status?: unknown;
  statusCode?: unknown;
};

function asHttpStatus(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isInteger(value) ? value : undefined;
}

export function getHttpStatus(error: unknown): number | undefined {
  if (!error || typeof error !== 'object') {
    return undefined;
  }

  const candidate = error as HttpErrorShape;

  return (
    asHttpStatus(candidate.response?.status)
    ?? asHttpStatus(candidate.status)
    ?? asHttpStatus(candidate.statusCode)
  );
}

export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  const status = getHttpStatus(error);

  // Auth, validation, rate-limit, and missing-resource errors should fail fast.
  if (status !== undefined && status >= 400 && status < 500) {
    return false;
  }

  return failureCount < MAX_QUERY_RETRY_ATTEMPTS;
}

export function exponentialRetryDelay(attemptIndex: number): number {
  return Math.min(1_000 * 2 ** attemptIndex, MAX_QUERY_RETRY_DELAY_MS);
}

export const queryClientDefaultOptions = {
  queries: {
    staleTime: QUERY_STALE_TIME_MS,
    gcTime: QUERY_GC_TIME_MS,
    retry: shouldRetryQuery,
    retryDelay: exponentialRetryDelay,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  },
  mutations: {
    retry: false,
    gcTime: MUTATION_GC_TIME_MS,
  },
} satisfies DefaultOptions;
