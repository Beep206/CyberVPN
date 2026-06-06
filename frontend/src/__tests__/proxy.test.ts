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

  it('redirects public dashboard route by Host header when runtime URL is local', () => {
    const req = createRequest(
      '/en-EN/dashboard?tab=ops',
      undefined,
      'http://127.0.0.1:9001',
      { host: 'cyber-vpn.net:9001' },
    );
    const res = proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net:9001/en-EN/dashboard?tab=ops');
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
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net:9001/en-EN/dashboard');
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
});
