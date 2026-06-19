// @vitest-environment node

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

function createRequest(
  path: string,
  cookies?: Record<string, string>,
  baseUrl = 'http://localhost:3000',
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
  return createRequest(path, undefined, 'http://cybervpn-frontend:3000', {
    host: 'cybervpn-frontend:3000',
    'x-forwarded-host': forwardedHost,
    'x-forwarded-proto': 'https',
  });
}

describe('proxy routing', () => {
  it('passes dashboard route through on cabinet host (auth handled by AuthGuard)', () => {
    const req = createRequest('/en-EN/dashboard/servers', undefined, 'https://my.cyber-vpn.net');
    const res = proxy(req);

    // No redirect — AuthGuard in the (dashboard) layout handles auth
    expect(res.status).toBe(200);
  });

  it('passes dashboard route with auth cookie through on cabinet host', () => {
    const req = createRequest('/en-EN/dashboard/servers', {
      access_token: 'some-token-value',
    }, 'https://my.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes support route through on cabinet host', () => {
    const req = createRequest('/ru-RU/support', undefined, 'https://my.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes public login route through', () => {
    const req = createRequest('/en-EN/login');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('redirects public dashboard route to cabinet host', () => {
    const req = createRequest('/ru-RU/dashboard/analytics', undefined, 'https://cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/ru-RU/dashboard/analytics');
  });

  it('redirects public support route to cabinet host', () => {
    const req = createRequest('/ru-RU/support', undefined, 'https://cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/ru-RU/support');
  });

  it('redirects public dashboard route by Host header when runtime URL is local', () => {
    const req = createRequest(
      '/en-EN/dashboard?tab=ops',
      undefined,
      'http://127.0.0.1:9001',
      { host: 'cyber-vpn.net:9001' },
    );
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/en-EN/dashboard?tab=ops');
  });

  it('redirects production proxied public dashboard routes without leaking the app port', () => {
    const req = createProxiedRequest('/en-EN/dashboard?tab=ops', 'cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/en-EN/dashboard?tab=ops');
  });

  it('redirects public delete-account route to cabinet host', () => {
    const req = createRequest('/ru-RU/delete-account', undefined, 'https://cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/ru-RU/delete-account');
  });

  it('passes delete-account route through on cabinet host', () => {
    const req = createRequest('/ru-RU/delete-account', undefined, 'https://my.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes register route through', () => {
    const req = createRequest('/en-EN/register');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('redirects admin mirror host to canonical admin host', () => {
    const req = createRequest('/en-EN/dashboard?tab=ops', undefined, 'https://admin.cyber-vpn.org');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://admin.cyber-vpn.net/en-EN/dashboard?tab=ops');
  });

  it('redirects cabinet root to localized dashboard', () => {
    const req = createRequest('/', undefined, 'https://my.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/en-EN/dashboard');
  });

  it('redirects cabinet root by Host header when runtime URL is local', () => {
    const req = createRequest(
      '/',
      undefined,
      'http://127.0.0.1:9001',
      { host: 'my.cyber-vpn.net:9001' },
    );
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/en-EN/dashboard');
  });

  it('redirects production proxied cabinet root without leaking the app port', () => {
    const req = createProxiedRequest('/', 'my.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/en-EN/dashboard');
  });

  it('keeps public marketing routes canonical on public host', () => {
    const req = createRequest('/ru-RU/pricing', undefined, 'https://cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('redirects marketing routes away from cabinet host', () => {
    const req = createRequest('/ru-RU/pricing', undefined, 'https://my.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://cyber-vpn.net/ru-RU/pricing');
  });

  it('redirects production proxied cabinet marketing routes to public origin without leaking the app port', () => {
    const req = createProxiedRequest('/ru-RU/pricing?currency=RUB', 'my.cyber-vpn.net');
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://cyber-vpn.net/ru-RU/pricing?currency=RUB');
  });

  it('does not reflect an untrusted forwarded host into redirect locations', () => {
    const req = createProxiedRequest('/ru-RU/dashboard', 'evil.example');
    const res = proxy(req);

    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });
});
