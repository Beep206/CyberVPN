// @vitest-environment node

import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET, POST } from './route';

function createContext(path: string[]) {
  return {
    params: Promise.resolve({ path }),
  };
}

function getFetchInit() {
  return (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[1] as RequestInit;
}

function readSetCookieHeaders(response: Response): string[] {
  const headers = response.headers as Headers & {
    getSetCookie?: () => string[];
  };

  if (typeof headers.getSetCookie === 'function') {
    return headers.getSetCookie();
  }

  const setCookie = response.headers.get('set-cookie');
  return setCookie ? [setCookie] : [];
}

describe('partner API proxy route', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it('proxies browser API calls through the canonical partner host boundary', async () => {
    vi.stubEnv('API_INTERNAL_ORIGIN', 'http://backend.local');
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ auth_realm_key: 'partner' }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
          'set-cookie': 'partner_access_token=next; Path=/api; HttpOnly',
        },
      }),
    ) as typeof fetch;

    const request = new NextRequest('http://portal.localhost:3004/api/v1/auth/session?probe=1', {
      headers: {
        'x-forwarded-host': 'portal.localhost:3004',
        'x-forwarded-proto': 'http',
        'x-request-id': 'req-1',
      },
    });
    request.cookies.set('partner_access_token', 'current');
    request.cookies.set('partner_refresh_token', 'refresh');

    const response = await GET(request, createContext(['auth', 'session']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(global.fetch).toHaveBeenCalledWith(
      'http://backend.local/api/v1/auth/session?probe=1',
      expect.objectContaining({
        method: 'GET',
        cache: 'no-store',
        redirect: 'manual',
      }),
    );
    expect(headers.get('x-forwarded-host')).toBe('portal.localhost:3004');
    expect(headers.get('x-forwarded-proto')).toBe('https');
    expect(headers.get('cookie')).toBe('partner_access_token=current; partner_refresh_token=refresh');
    expect(headers.get('x-request-id')).toBe('req-1');
    expect(response.status).toBe(200);
    expect(readSetCookieHeaders(response).join('\\n')).toContain('partner_access_token=next');
    await expect(response.json()).resolves.toEqual({ auth_realm_key: 'partner' });
  });

  it('forwards mutating request bodies with canonical partner CSRF headers for approved local-stage origins', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    global.fetch = vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ) as typeof fetch;

    const request = new NextRequest('http://portal.localhost:3004/api/v1/auth/logout', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'http://portal.localhost:3004',
        referer: 'http://portal.localhost:3004/en-EN/dashboard',
        'x-forwarded-host': 'portal.localhost:3004',
      },
      body: JSON.stringify({}),
    });

    const response = await POST(request, createContext(['auth', 'logout']));
    const init = getFetchInit();
    const headers = init.headers as Headers;
    const body = init.body as ArrayBuffer;

    expect(global.fetch).toHaveBeenCalledWith(
      'http://backend.internal/api/v1/auth/logout',
      expect.objectContaining({
        method: 'POST',
        cache: 'no-store',
        redirect: 'manual',
      }),
    );
    expect(headers.get('x-forwarded-host')).toBe('portal.localhost:3004');
    expect(headers.get('x-forwarded-proto')).toBe('https');
    expect(headers.get('origin')).toBe('https://portal.localhost:3004');
    expect(headers.get('referer')).toBe('https://portal.localhost:3004/en-EN/dashboard');
    expect(headers.get('content-type')).toBe('application/json');
    expect(new TextDecoder().decode(body)).toBe('{}');
    expect(response.status).toBe(204);
  });

  it('preserves foreign origins so backend CSRF can reject cross-site cookie requests', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal');
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'CSRF origin validation failed' }), {
        status: 403,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ) as typeof fetch;

    const request = new NextRequest('http://portal.localhost:3004/api/v1/auth/logout', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'https://evil.example',
        referer: 'https://evil.example/logout',
      },
      body: JSON.stringify({}),
    });

    const response = await POST(request, createContext(['auth', 'logout']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(headers.get('origin')).toBe('https://evil.example');
    expect(headers.get('referer')).toBe('https://evil.example/logout');
    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual({ detail: 'CSRF origin validation failed' });
  });
});
