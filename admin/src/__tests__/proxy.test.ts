import { describe, it, expect, vi } from 'vitest';
import { NextRequest } from 'next/server';

// Mock next-intl/middleware to pass through
vi.mock('next-intl/middleware', () => ({
  default: () => () => new Response(null, { status: 200 }),
}));

vi.mock('@/i18n/config', () => ({
  locales: ['ru-RU', 'en-EN'],
  defaultLocale: 'ru-RU',
}));

// Import after mocks
const { proxy } = await import('../proxy');

function createRequest(path: string, cookies?: Record<string, string>): NextRequest {
  const url = new URL(path, 'http://localhost:3001');
  const req = new NextRequest(url);
  if (cookies) {
    for (const [name, value] of Object.entries(cookies)) {
      req.cookies.set(name, value);
    }
  }
  return req;
}

describe('proxy routing', () => {
  it('redirects localized root routes to localized login', () => {
    const req = createRequest('/en-EN');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3001/en-EN/login');
  });

  it('passes dashboard route through to intlMiddleware (auth handled by AuthGuard)', () => {
    const req = createRequest('/en-EN/infrastructure');
    const res = proxy(req);

    // No redirect — AuthGuard in the (dashboard) layout handles auth
    expect(res.status).toBe(200);
  });

  it('passes dashboard route with auth cookie through', () => {
    const req = createRequest('/en-EN/governance', {
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
    const req = createRequest('/ru-RU/dashboard');
    const res = proxy(req);

    // No redirect — auth is handled client-side by AuthGuard
    expect(res.status).toBe(200);
  });

  it('normalizes unsupported locale prefixes to the default locale', () => {
    const req = createRequest('/zh-CN/login');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3001/ru-RU/login');
  });
});
