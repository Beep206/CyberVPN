/**
 * Sentry Configuration Validation Tests
 *
 * Tests that Sentry client config properly:
 * - Imports and calls Sentry.init
 * - Reads DSN from environment variable
 * - Sets tracesSampleRate based on NODE_ENV
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('Sentry Client Configuration', () => {
  let mockSentryInit: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // Mock Sentry module
    mockSentryInit = vi.fn();
    vi.doMock('@sentry/nextjs', () => ({
      init: mockSentryInit,
      browserTracingIntegration: vi.fn(() => 'browserTracingIntegration'),
      replayIntegration: vi.fn(() => 'replayIntegration'),
    }));
  });

  afterEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.unstubAllEnvs();
  });

  it('calls Sentry.init when imported', async () => {
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', 'https://test@sentry.io/123');
    vi.stubEnv('NODE_ENV', 'test');

    // Dynamic import to trigger config execution
    await import('../sentry.client.config');

    expect(mockSentryInit).toHaveBeenCalledTimes(1);
  });

  it('reads DSN from NEXT_PUBLIC_SENTRY_DSN environment variable', async () => {
    const testDsn = 'https://test-dsn@sentry.io/456';
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', testDsn);
    vi.stubEnv('NODE_ENV', 'test');

    await import('../sentry.client.config');

    expect(mockSentryInit).toHaveBeenCalledWith(
      expect.objectContaining({
        dsn: testDsn,
      })
    );
  });

  it('sets tracesSampleRate to 1.0 in non-production environments', async () => {
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', 'https://test@sentry.io/123');
    vi.stubEnv('NODE_ENV', 'development');

    await import('../sentry.client.config');

    expect(mockSentryInit).toHaveBeenCalledWith(
      expect.objectContaining({
        tracesSampleRate: 1.0,
      })
    );
  });

  it('sets tracesSampleRate to 0.2 in production environment', async () => {
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', 'https://test@sentry.io/123');
    vi.stubEnv('NODE_ENV', 'production');

    await import('../sentry.client.config');

    expect(mockSentryInit).toHaveBeenCalledWith(
      expect.objectContaining({
        tracesSampleRate: 0.2,
      })
    );
  });

  it('sets environment to NODE_ENV value', async () => {
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', 'https://test@sentry.io/123');
    vi.stubEnv('NODE_ENV', 'staging');

    await import('../sentry.client.config');

    expect(mockSentryInit).toHaveBeenCalledWith(
      expect.objectContaining({
        environment: 'staging',
      })
    );
  });

  it('includes browser tracing and replay integrations', async () => {
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', 'https://test@sentry.io/123');
    vi.stubEnv('NODE_ENV', 'test');

    await import('../sentry.client.config');

    expect(mockSentryInit).toHaveBeenCalledWith(
      expect.objectContaining({
        integrations: expect.arrayContaining([
          'browserTracingIntegration',
          'replayIntegration',
        ]),
      })
    );
  });
});
