/**
 * Sentry Configuration Validation Tests
 *
 * Tests that Sentry client instrumentation properly:
 * - Imports and calls Sentry.init
 * - Reads DSN from environment variable
 * - Sets tracesSampleRate based on NODE_ENV
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('Sentry Client Configuration', () => {
  let mockSentryInit: ReturnType<typeof vi.fn>;

  function stubBrowser() {
    vi.stubGlobal('window', {
      requestIdleCallback: (callback: () => void) => callback(),
      setTimeout,
    });
  }

  beforeEach(() => {
    mockSentryInit = vi.fn();
    vi.doMock('@sentry/nextjs', () => ({
      init: mockSentryInit,
      browserTracingIntegration: vi.fn(() => 'browserTracingIntegration'),
      replayIntegration: vi.fn(() => 'replayIntegration'),
      captureRouterTransitionStart: vi.fn(),
    }));
  });

  afterEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it('calls Sentry.init when imported', async () => {
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', 'https://test@sentry.io/123');
    vi.stubEnv('NODE_ENV', 'test');
    stubBrowser();

    await import('../instrumentation-client');

    expect(mockSentryInit).toHaveBeenCalledTimes(1);
  });

  it('reads DSN from NEXT_PUBLIC_SENTRY_DSN environment variable', async () => {
    const testDsn = 'https://test-dsn@sentry.io/456';
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', testDsn);
    vi.stubEnv('NODE_ENV', 'test');
    stubBrowser();

    await import('../instrumentation-client');

    expect(mockSentryInit).toHaveBeenCalledWith(
      expect.objectContaining({
        dsn: testDsn,
      }),
    );
  });

  it('sets tracesSampleRate to 1.0 in non-production environments', async () => {
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', 'https://test@sentry.io/123');
    vi.stubEnv('NODE_ENV', 'development');
    stubBrowser();

    await import('../instrumentation-client');

    expect(mockSentryInit).toHaveBeenCalledWith(
      expect.objectContaining({
        tracesSampleRate: 1.0,
      }),
    );
  });

  it('sets tracesSampleRate to 0.2 in production environment', async () => {
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', 'https://test@sentry.io/123');
    vi.stubEnv('NODE_ENV', 'production');
    stubBrowser();

    await import('../instrumentation-client');

    expect(mockSentryInit).toHaveBeenCalledWith(
      expect.objectContaining({
        tracesSampleRate: 0.2,
      }),
    );
  });

  it('sets environment to NODE_ENV value', async () => {
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', 'https://test@sentry.io/123');
    vi.stubEnv('NODE_ENV', 'staging');
    stubBrowser();

    await import('../instrumentation-client');

    expect(mockSentryInit).toHaveBeenCalledWith(
      expect.objectContaining({
        environment: 'staging',
      }),
    );
  });

  it('includes browser tracing and replay integrations', async () => {
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', 'https://test@sentry.io/123');
    vi.stubEnv('NODE_ENV', 'test');
    stubBrowser();

    await import('../instrumentation-client');

    expect(mockSentryInit).toHaveBeenCalledWith(
      expect.objectContaining({
        integrations: expect.arrayContaining([
          'browserTracingIntegration',
          'replayIntegration',
        ]),
      }),
    );
  });
});
