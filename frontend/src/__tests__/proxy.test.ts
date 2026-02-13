import { describe, it, expect, vi } from 'vitest';
import { NextRequest } from 'next/server';

// Mock next-intl/middleware to pass through
vi.mock('next-intl/middleware', () => ({
  default: () => () => new Response(null, { status: 200 }),
}));

vi.mock('@/i18n/config', () => ({
  locales: ['en-EN', 'ru-RU'],
  defaultLocale: 'en-EN',
}));

// Import after mocks
const { proxy } = await import('../proxy');

function createRequest(path: string, cookies?: Record<string, string>): NextRequest {
  const url = new URL(path, 'http://localhost:3000');
  const req = new NextRequest(url);
  if (cookies) {
    for (const [name, value] of Object.entries(cookies)) {
      req.cookies.set(name, value);
    }
  }
  return req;
}

describe('proxy routing', () => {
  it('passes dashboard route through to intlMiddleware (auth handled by AuthGuard)', () => {
    const req = createRequest('/en-EN/dashboard/servers');
    const res = proxy(req);

    // No redirect — AuthGuard in the (dashboard) layout handles auth
    expect(res.status).toBe(200);
  });

  it('passes dashboard route with auth cookie through', () => {
    const req = createRequest('/en-EN/dashboard/servers', {
      access_token: 'some-token-value',
    });
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes public login route through', () => {
    const req = createRequest('/en-EN/login');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes ru-RU dashboard route through without redirect', () => {
    const req = createRequest('/ru-RU/dashboard/analytics');
    const res = proxy(req);

    // No redirect — auth is handled client-side by AuthGuard
    expect(res.status).toBe(200);
  });

  it('passes register route through', () => {
    const req = createRequest('/en-EN/register');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });
});
