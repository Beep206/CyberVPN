import { describe, expect, it } from 'vitest';
import { AxiosError, AxiosHeaders } from 'axios';
import { RateLimitError } from '@/lib/api/client';
import {
  isRecoverablePartnerPortalResourceState,
  normalizePartnerPortalResourceState,
} from './resource-state';
import {
  boundedWorkspaceRetry,
  boundedWorkspaceRetryDelay,
  resolvePortalResource,
} from './use-partner-portal-runtime-state';

function axiosStatusError(status: number): unknown {
  return {
    isAxiosError: true,
    response: { status },
  };
}

function realAxiosStatusError(status: number): AxiosError {
  return new AxiosError(
    `HTTP ${status}`,
    'ERR_BAD_RESPONSE',
    undefined,
    undefined,
    {
      status,
      statusText: String(status),
      headers: {},
      config: { headers: new AxiosHeaders() },
      data: {},
    },
  );
}

describe('partner portal resource state normalization', () => {
  it('normalizes disabled, loading, empty, and ready query states without inventing data', () => {
    expect(
      normalizePartnerPortalResourceState({
        data: null,
        error: null,
        isError: false,
        isLoading: false,
      }, { enabled: false }),
    ).toEqual({ status: 'idle' });

    expect(
      normalizePartnerPortalResourceState({
        data: null,
        error: null,
        isError: false,
        isLoading: true,
      }),
    ).toEqual({ status: 'loading' });

    expect(
      normalizePartnerPortalResourceState({
        data: [],
        error: null,
        isError: false,
        isLoading: false,
      }, { isEmpty: (items) => items.length === 0 }),
    ).toEqual({ status: 'empty', data: [] });

    expect(
      normalizePartnerPortalResourceState({
        data: [{ id: 'code-1' }],
        error: null,
        isError: false,
        isLoading: false,
      }, { isEmpty: (items) => items.length === 0 }),
    ).toEqual({ status: 'ready', data: [{ id: 'code-1' }] });
  });

  it('keeps auth failures forbidden and provider degradation recoverable', () => {
    const forbidden = normalizePartnerPortalResourceState({
      data: null,
      error: axiosStatusError(403),
      isError: true,
      isLoading: false,
    });
    const missing = normalizePartnerPortalResourceState({
      data: null,
      error: axiosStatusError(404),
      isError: true,
      isLoading: false,
    });
    const degraded = normalizePartnerPortalResourceState({
      data: null,
      error: axiosStatusError(503),
      isError: true,
      isLoading: false,
    });
    const rateLimited = normalizePartnerPortalResourceState({
      data: null,
      error: new RateLimitError(45),
      isError: true,
      isLoading: false,
    });

    expect(forbidden).toEqual({
      status: 'forbidden',
      error: { statusCode: 403, code: 'forbidden', message: 'resource_error' },
    });
    expect(isRecoverablePartnerPortalResourceState(forbidden)).toBe(false);

    expect(missing).toEqual({
      status: 'unavailable',
      error: { statusCode: 404, code: 'not_found', message: 'resource_error' },
    });
    expect(isRecoverablePartnerPortalResourceState(missing)).toBe(false);

    expect(degraded).toEqual({
      status: 'unavailable',
      error: { statusCode: 503, code: 'temporarily_unavailable', message: 'resource_error' },
    });
    expect(isRecoverablePartnerPortalResourceState(degraded)).toBe(true);

    expect(rateLimited).toEqual({
      status: 'unavailable',
      error: {
        statusCode: 429,
        code: 'rate_limited',
        message: 'Rate limited. Try again in 45 seconds',
        retryAfterSeconds: 45,
      },
    });
    expect(isRecoverablePartnerPortalResourceState(rateLimited)).toBe(true);
  });
});

describe('partner portal workspace retry policy', () => {
  it('does not retry auth/not-found failures but bounds degraded and rate-limited retries', () => {
    expect(boundedWorkspaceRetry(0, realAxiosStatusError(401))).toBe(false);
    expect(boundedWorkspaceRetry(0, realAxiosStatusError(403))).toBe(false);
    expect(boundedWorkspaceRetry(0, realAxiosStatusError(404))).toBe(false);

    expect(boundedWorkspaceRetry(0, realAxiosStatusError(503))).toBe(true);
    expect(boundedWorkspaceRetry(1, realAxiosStatusError(503))).toBe(true);
    expect(boundedWorkspaceRetry(2, realAxiosStatusError(503))).toBe(false);

    expect(boundedWorkspaceRetry(0, new RateLimitError(90))).toBe(true);
    expect(boundedWorkspaceRetry(1, new RateLimitError(90))).toBe(true);
    expect(boundedWorkspaceRetry(2, new RateLimitError(90))).toBe(false);
  });

  it('uses Retry-After for rate limits and caps exponential degraded retry delay', () => {
    expect(boundedWorkspaceRetryDelay(0, new RateLimitError(45))).toBe(45_000);
    expect(boundedWorkspaceRetryDelay(0, new RateLimitError(180))).toBe(120_000);
    expect(boundedWorkspaceRetryDelay(0, realAxiosStatusError(503))).toBe(1_000);
    expect(boundedWorkspaceRetryDelay(10, realAxiosStatusError(503))).toBe(30_000);
  });
});

describe('partner portal resource loading boundary', () => {
  it('propagates forbidden and missing resources instead of converting them to empty data', async () => {
    await expect(
      resolvePortalResource(() => Promise.reject(realAxiosStatusError(403))),
    ).rejects.toMatchObject({
      response: { status: 403 },
    });

    await expect(
      resolvePortalResource(() => Promise.reject(realAxiosStatusError(404))),
    ).rejects.toMatchObject({
      response: { status: 404 },
    });
  });
});
