import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('next-intl/plugin', () => ({
  default: () => <T>(config: T) => config,
}));

vi.mock('@sentry/nextjs', () => ({
  withSentryConfig: <T>(config: T) => config,
}));

const originalPartnerApiUrl = process.env.PARTNER_API_URL;
const originalNextPublicApiUrl = process.env.NEXT_PUBLIC_API_URL;

async function loadNextConfig() {
  vi.resetModules();
  return import('../../next.config');
}

describe('partner next config', () => {
  afterEach(() => {
    if (originalPartnerApiUrl === undefined) {
      delete process.env.PARTNER_API_URL;
    } else {
      process.env.PARTNER_API_URL = originalPartnerApiUrl;
    }

    if (originalNextPublicApiUrl === undefined) {
      delete process.env.NEXT_PUBLIC_API_URL;
    } else {
      process.env.NEXT_PUBLIC_API_URL = originalNextPublicApiUrl;
    }
  });

  it('rewrites local partner API calls to the approved local-stage backend by default', async () => {
    delete process.env.PARTNER_API_URL;
    delete process.env.NEXT_PUBLIC_API_URL;

    const { resolvePartnerApiRewriteDestination } = await loadNextConfig();

    expect(resolvePartnerApiRewriteDestination()).toBe('http://127.0.0.1:18080/api/v1/:path*');
  });

  it('uses explicit partner backend origin when provided', async () => {
    process.env.PARTNER_API_URL = 'http://localhost:8000';
    process.env.NEXT_PUBLIC_API_URL = 'http://127.0.0.1:18080';

    const { resolvePartnerApiRewriteDestination } = await loadNextConfig();

    expect(resolvePartnerApiRewriteDestination()).toBe('http://localhost:8000/api/v1/:path*');
  });

  it('accepts NEXT_PUBLIC_API_URL values with or without the canonical API suffix', async () => {
    delete process.env.PARTNER_API_URL;
    process.env.NEXT_PUBLIC_API_URL = 'http://127.0.0.1:18080/api/v1/';

    const { resolvePartnerApiRewriteDestination } = await loadNextConfig();

    expect(resolvePartnerApiRewriteDestination()).toBe('http://127.0.0.1:18080/api/v1/:path*');
  });
});
