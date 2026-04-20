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

function createRequest(
  path: string,
  options?: {
    host?: string;
    cookies?: Record<string, string>;
  },
): NextRequest {
  const host = options?.host ?? 'localhost:3002';
  const url = new URL(path, `http://${host}`);
  const req = new NextRequest(url, {
    headers: {
      host,
      'x-forwarded-host': host,
    },
  });
  if (options?.cookies) {
    for (const [name, value] of Object.entries(options.cookies)) {
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
    expect(res.headers.get('location')).toBe('http://localhost:3002/en-EN/login');
  });

  it('keeps localized root on storefront hosts for public storefront rendering', () => {
    const req = createRequest('/en-EN', { host: 'storefront.localhost:3002' });
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes dashboard route through to intlMiddleware (auth handled by AuthGuard)', () => {
    const req = createRequest('/en-EN/infrastructure');
    const res = proxy(req);

    // No redirect — AuthGuard in the (dashboard) layout handles auth
    expect(res.status).toBe(200);
  });

  it('passes dashboard route with auth cookie through', () => {
    const req = createRequest('/en-EN/governance', {
      cookies: {
        access_token: 'some-token-value',
      },
    });
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes public login route through', () => {
    const req = createRequest('/en-EN/login');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes public register route through', () => {
    const req = createRequest('/en-EN/register');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes forgot-password route through', () => {
    const req = createRequest('/ru-RU/forgot-password');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes ru-RU dashboard route through without redirect', () => {
    const req = createRequest('/ru-RU/dashboard');
    const res = proxy(req);

    // No redirect — auth is handled client-side by AuthGuard
    expect(res.status).toBe(200);
  });

  it('redirects portal workspace routes away from storefront hosts', () => {
    const req = createRequest('/ru-RU/dashboard', { host: 'storefront.localhost:3002' });
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://storefront.localhost:3002/ru-RU');
  });

  it('redirects storefront commerce routes away from portal hosts', () => {
    const req = createRequest('/ru-RU/checkout');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3002/ru-RU/login');
  });

  it('normalizes unsupported locale prefixes to the default locale', () => {
    const req = createRequest('/zh-CN/login');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3002/ru-RU/login');
  });
});
