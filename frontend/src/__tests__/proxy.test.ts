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

describe('proxy auth redirect', () => {
  it('redirects dashboard route without auth cookie to login', () => {
    const req = createRequest('/en-EN/dashboard/servers');
    const res = proxy(req);

    expect(res.status).toBe(307);
    const location = res.headers.get('location');
    expect(location).toContain('/en-EN/login');
    expect(location).toContain('redirect=%2Fen-EN%2Fdashboard%2Fservers');
  });

  it('passes through dashboard route with auth cookie', () => {
    const req = createRequest('/en-EN/dashboard/servers', {
      access_token: 'some-token-value',
    });
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('does not redirect public login route without cookie', () => {
    const req = createRequest('/en-EN/login');
    const res = proxy(req);

    expect(res.status).toBe(200);
  });

  it('redirects ru-RU dashboard route without cookie', () => {
    const req = createRequest('/ru-RU/dashboard/analytics');
    const res = proxy(req);

    expect(res.status).toBe(307);
    const location = res.headers.get('location');
    expect(location).toContain('/ru-RU/login');
  });

  it('includes redirect query param with original path', () => {
    const req = createRequest('/en-EN/dashboard/users');
    const res = proxy(req);

    const location = new URL(res.headers.get('location')!);
    expect(location.searchParams.get('redirect')).toBe(
      '/en-EN/dashboard/users',
    );
  });
});
