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
    runtimeHost?: string;
    forwardedHost?: string;
    forwardedProto?: string;
    cookies?: Record<string, string>;
  },
): NextRequest {
  const host = options?.host ?? 'localhost:3002';
  const runtimeHost = options?.runtimeHost ?? host;
  const forwardedHost = options?.forwardedHost ?? host;
  const url = new URL(path, `http://${runtimeHost}`);
  const req = new NextRequest(url, {
    headers: {
      host: runtimeHost,
      'x-forwarded-host': forwardedHost,
      ...(options?.forwardedProto ? { 'x-forwarded-proto': options.forwardedProto } : {}),
    },
  });
  if (options?.cookies) {
    for (const [name, value] of Object.entries(options.cookies)) {
      req.cookies.set(name, value);
    }
  }
  return req;
}

function createProxiedRequest(path: string, forwardedHost: string): NextRequest {
  return createRequest(path, {
    runtimeHost: 'cybervpn-partner:3002',
    forwardedHost,
    forwardedProto: 'https',
  });
}

describe('proxy routing', () => {
  it('redirects localized root routes to localized login', () => {
    const req = createRequest('/en-EN');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3002/en-EN/login');
  });

  it('redirects production proxied localized root without leaking the app port', () => {
    const req = createProxiedRequest('/en-EN', 'partner.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://partner.cyber-vpn.net/en-EN/login');
  });

  it('keeps localized root on storefront hosts for public storefront rendering', () => {
    const req = createRequest('/en-EN', { host: 'storefront.localhost:3002' });
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes dashboard route through to intlMiddleware (auth handled by AuthGuard)', () => {
    const req = createRequest('/en-EN/analytics');
    const res = proxy(req);

    // No redirect — AuthGuard in the (dashboard) layout handles auth
    expect(res.status).toBe(200);
  });

  it('passes dashboard route with auth cookie through', () => {
    const req = createRequest('/en-EN/team', {
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

  it('retires localized legacy admin routes before they render in the partner app', () => {
    const req = createRequest('/en-EN/_legacy-admin-routes/growth/promo-codes?tab=active');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3002/en-EN/codes');
  });

  it('retires sensitive legacy infrastructure routes to the dashboard', () => {
    const req = createRequest('/ru-RU/_legacy-admin-routes/infrastructure/servers');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3002/ru-RU/dashboard');
  });

  it('retires legacy admin routes away from storefront hosts without entering workspace routes', () => {
    const req = createRequest('/en-EN/_legacy-admin-routes/commerce/payments', {
      host: 'storefront.localhost:3002',
    });
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://storefront.localhost:3002/en-EN');
  });

  it('returns 404 for retired generic localized partner section routes', () => {
    const req = createRequest('/en-EN/not-a-real-section');
    const res = proxy(req);

    expect(res.status).toBe(404);
    expect(res.headers.get('cache-control')).toBe('no-store');
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

  it('redirects production proxied storefront commerce routes without leaking the app port', () => {
    const req = createProxiedRequest('/ru-RU/checkout?plan=plus', 'partner.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://partner.cyber-vpn.net/ru-RU/login');
  });

  it('normalizes unsupported locale prefixes to the default locale', () => {
    const req = createRequest('/zh-CN/login');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3002/ru-RU/login');
  });

  it('normalizes production proxied unsupported locale prefixes without leaking the app port', () => {
    const req = createProxiedRequest('/zh-CN/login?next=%2Fen-EN', 'partner.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://partner.cyber-vpn.net/ru-RU/login?next=%2Fen-EN');
  });

  it('falls back to the canonical storefront host instead of reflecting unknown forwarded hosts', () => {
    const req = createProxiedRequest('/zh-CN/login', 'evil.example');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://storefront.cyber-vpn.net/ru-RU/login');
  });
});
