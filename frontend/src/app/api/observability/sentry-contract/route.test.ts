import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET } from './route';

function createRequest(secret?: string) {
  return new NextRequest(
    'http://localhost:3000/api/observability/sentry-contract',
    {
      headers: secret
        ? {
            'x-observability-secret': secret,
          }
        : undefined,
    },
  );
}

describe('GET /api/observability/sentry-contract', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('rejects requests without the internal secret', async () => {
    vi.stubEnv('FRONTEND_OBSERVABILITY_INTERNAL_SECRET', 'expected-secret');

    const response = await GET(createRequest());

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual({
      detail: 'Forbidden',
    });
  });

  it('returns the resolved Sentry contract for authorized requests', async () => {
    vi.stubEnv('FRONTEND_OBSERVABILITY_INTERNAL_SECRET', 'expected-secret');
    vi.stubEnv('APP_ENV', 'staging');
    vi.stubEnv('SENTRY_RELEASE', 'frontend@abc123');
    vi.stubEnv('SENTRY_DSN', 'https://server@example.com/1');
    vi.stubEnv('NEXT_PUBLIC_SENTRY_DSN', 'https://public@example.com/1');

    const response = await GET(createRequest('expected-secret'));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      runtimeSurface: 'frontend',
      environment: 'staging',
      release: 'frontend@abc123',
      dsnConfigured: true,
      publicDsnConfigured: true,
    });
  });
});
