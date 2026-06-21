import { AxiosError } from 'axios';
import { RateLimitError } from '@/lib/api/client';

export type PartnerPortalResourceStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'empty'
  | 'forbidden'
  | 'unavailable'
  | 'error';

export interface PartnerPortalResourceError {
  statusCode: number | null;
  code: string;
  message: string;
  retryAfterSeconds?: number;
}

export type PartnerPortalResourceState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; data: T }
  | { status: 'empty'; data: T | null }
  | { status: 'forbidden'; error: PartnerPortalResourceError }
  | { status: 'unavailable'; error: PartnerPortalResourceError }
  | { status: 'error'; error: PartnerPortalResourceError };

type QueryLike<T> = {
  data?: T | null;
  error?: unknown;
  isError: boolean;
  isFetching?: boolean;
  isLoading: boolean;
};

export function getPortalApiStatusCode(error: unknown): number | null {
  if (error instanceof AxiosError) {
    return error.response?.status ?? null;
  }

  const maybeAxiosError = error as {
    isAxiosError?: boolean;
    response?: { status?: unknown };
  };
  if (maybeAxiosError?.isAxiosError && typeof maybeAxiosError.response?.status === 'number') {
    return maybeAxiosError.response.status;
  }

  return null;
}

export function normalizePortalResourceError(error: unknown): PartnerPortalResourceError {
  if (error instanceof RateLimitError) {
    return {
      statusCode: 429,
      code: 'rate_limited',
      message: error.message,
      retryAfterSeconds: error.retryAfter,
    };
  }

  const statusCode = getPortalApiStatusCode(error);
  const message = error instanceof Error ? error.message : 'resource_error';

  if (statusCode === 401 || statusCode === 403) {
    return { statusCode, code: 'forbidden', message };
  }
  if (statusCode === 404) {
    return { statusCode, code: 'not_found', message };
  }
  if (statusCode === 502 || statusCode === 503 || statusCode === 504) {
    return { statusCode, code: 'temporarily_unavailable', message };
  }
  if (statusCode === 429) {
    return { statusCode, code: 'rate_limited', message };
  }

  return {
    statusCode,
    code: statusCode == null ? 'network_error' : 'unexpected_error',
    message,
  };
}

export function normalizePartnerPortalResourceState<T>(
  query: QueryLike<T>,
  options: {
    enabled?: boolean;
    isEmpty?: (data: T) => boolean;
  } = {},
): PartnerPortalResourceState<T> {
  if (options.enabled === false) {
    return { status: 'idle' };
  }

  if (query.isLoading && query.data == null) {
    return { status: 'loading' };
  }

  if (query.isError) {
    const error = normalizePortalResourceError(query.error);
    if (error.statusCode === 401 || error.statusCode === 403) {
      return { status: 'forbidden', error };
    }
    if (
      error.statusCode === 404
      || error.statusCode === 429
      || error.statusCode === 502
      || error.statusCode === 503
      || error.statusCode === 504
    ) {
      return { status: 'unavailable', error };
    }
    return { status: 'error', error };
  }

  if (query.data == null) {
    return { status: 'empty', data: query.data as T };
  }

  if (options.isEmpty?.(query.data)) {
    return { status: 'empty', data: query.data };
  }

  return { status: 'ready', data: query.data };
}

export function isRecoverablePartnerPortalResourceState(
  state: PartnerPortalResourceState<unknown>,
): boolean {
  return (
    state.status === 'error'
    || (
      state.status === 'unavailable'
      && state.error.code !== 'not_found'
    )
  );
}
