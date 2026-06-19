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
  cookies?: Record<string, string>,
  baseUrl = 'http://localhost:3001',
  headers?: HeadersInit,
): NextRequest {
  const url = new URL(path, baseUrl);
  const req = new NextRequest(url, { headers });
  if (cookies) {
    for (const [name, value] of Object.entries(cookies)) {
      req.cookies.set(name, value);
    }
  }
  return req;
}

function createProxiedRequest(path: string, forwardedHost: string): NextRequest {
  return createRequest(path, undefined, 'http://cybervpn-admin:3001', {
    host: 'cybervpn-admin:3001',
    'x-forwarded-host': forwardedHost,
    'x-forwarded-proto': 'https',
  });
}

describe('proxy routing', () => {
  it('redirects localized root routes to localized login', () => {
    const req = createRequest('/en-EN');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3001/en-EN/login');
  });

  it('redirects production proxied localized root without leaking the app port', () => {
    const req = createProxiedRequest('/en-EN', 'admin.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://admin.cyber-vpn.net/en-EN/login');
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

  it('normalizes production proxied unsupported locale prefixes without leaking the app port', () => {
    const req = createProxiedRequest('/zh-CN/login?next=%2Fen-EN', 'admin.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://admin.cyber-vpn.net/ru-RU/login?next=%2Fen-EN');
  });

  it('falls back to canonical admin origin for untrusted forwarded hosts', () => {
    const req = createProxiedRequest('/zh-CN/login', 'evil.example');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://admin.cyber-vpn.net/ru-RU/login');
  });
});
