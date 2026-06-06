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

describe('admin API proxy route', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it('proxies browser API calls through the canonical admin host boundary', async () => {
    vi.stubEnv('API_INTERNAL_ORIGIN', 'http://backend.local');
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ role: 'operator' }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
          'set-cookie': 'access_token=next; Path=/api; HttpOnly',
        },
      }),
    ) as typeof fetch;

    const request = new NextRequest('http://127.0.0.1:13001/api/v1/auth/session?probe=1', {
      headers: {
        'x-forwarded-host': '127.0.0.1:13001',
        'x-forwarded-proto': 'http',
        'x-request-id': 'req-1',
      },
    });
    request.cookies.set('access_token', 'current');
    request.cookies.set('refresh_token', 'refresh');

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
    expect(headers.get('x-forwarded-host')).toBe('admin.cyber-vpn.net');
    expect(headers.get('x-forwarded-proto')).toBe('https');
    expect(headers.get('cookie')).toBe('access_token=current; refresh_token=refresh');
    expect(headers.get('x-request-id')).toBe('req-1');
    expect(response.status).toBe(200);
    expect(readSetCookieHeaders(response).join('\n')).toContain('access_token=next');
    await expect(response.json()).resolves.toEqual({ role: 'operator' });
  });

  it('forwards mutating request bodies with canonical realm and CSRF headers for approved local-stage admin', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    global.fetch = vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ) as typeof fetch;

    const request = new NextRequest('http://127.0.0.1:13001/api/v1/auth/logout', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'http://127.0.0.1:13001',
        referer: 'http://127.0.0.1:13001/en-EN/dashboard',
        'x-forwarded-host': 'localhost:13001',
      },
      body: JSON.stringify({ refresh_token: 'synthetic-test-token' }),
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
    expect(headers.get('x-forwarded-host')).toBe('admin.cyber-vpn.net');
    expect(headers.get('x-forwarded-proto')).toBe('https');
    expect(headers.get('origin')).toBe('https://admin.cyber-vpn.net');
    expect(headers.get('referer')).toBe('https://admin.cyber-vpn.net/en-EN/dashboard');
    expect(headers.get('content-type')).toBe('application/json');
    expect(new TextDecoder().decode(body)).toBe('{"refresh_token":"synthetic-test-token"}');
    expect(response.status).toBe(204);
  });

  it('canonicalizes approved local-stage source headers when served on the container port', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    global.fetch = vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ) as typeof fetch;

    const request = new NextRequest('http://127.0.0.1:3000/api/v1/auth/logout', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'http://127.0.0.1:13001',
        referer: 'http://127.0.0.1:13001/en-EN/dashboard',
      },
      body: JSON.stringify({}),
    });

    const response = await POST(request, createContext(['auth', 'logout']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(headers.get('origin')).toBe('https://admin.cyber-vpn.net');
    expect(headers.get('referer')).toBe('https://admin.cyber-vpn.net/en-EN/dashboard');
    expect(response.status).toBe(204);
  });

  it('canonicalizes localhost local-stage admin origins for backend CSRF allowlists', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    global.fetch = vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ) as typeof fetch;

    const request = new NextRequest('http://localhost:13001/api/v1/auth/logout', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'http://localhost:13001',
        referer: 'http://localhost:13001/en-EN/dashboard',
      },
      body: JSON.stringify({}),
    });

    const response = await POST(request, createContext(['auth', 'logout']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(headers.get('origin')).toBe('https://admin.cyber-vpn.net');
    expect(headers.get('referer')).toBe('https://admin.cyber-vpn.net/en-EN/dashboard');
    expect(response.status).toBe(204);
  });


  it('preserves local-stage Origin and Referer for passkey WebAuthn ceremonies', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ challengeId: 'synthetic-challenge' }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ) as typeof fetch;

    const request = new NextRequest('http://localhost:13001/api/v1/auth/passkeys/registration/options', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'http://localhost:13001',
        referer: 'http://localhost:13001/en-EN/passkeys',
      },
      body: JSON.stringify({ label: 'CYBA-531 synthetic' }),
    });

    const response = await POST(request, createContext(['auth', 'passkeys', 'registration', 'options']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(headers.get('x-forwarded-host')).toBe('admin.cyber-vpn.net');
    expect(headers.get('x-forwarded-proto')).toBe('https');
    expect(headers.get('origin')).toBe('http://localhost:13001');
    expect(headers.get('referer')).toBe('http://localhost:13001/en-EN/passkeys');
    expect(response.status).toBe(200);
  });

  it('strips Secure from passkey auth cookies for approved local-stage admin origin', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ requires_2fa: false }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
          'set-cookie': 'access_token=backend_access; Path=/api; HttpOnly; Secure; SameSite=Lax',
        },
      }),
    ) as typeof fetch;

    const request = new NextRequest('http://localhost:13001/api/v1/auth/passkeys/authentication/verify', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'http://localhost:13001',
      },
      body: JSON.stringify({ challengeId: 'synthetic-challenge', credential: {} }),
    });

    const response = await POST(request, createContext(['auth', 'passkeys', 'authentication', 'verify']));
    const setCookieHeaders = readSetCookieHeaders(response).join('\n');

    expect(response.status).toBe(200);
    expect(setCookieHeaders).toContain('access_token=backend_access');
    expect(setCookieHeaders).toContain('HttpOnly');
    expect(setCookieHeaders).not.toContain('Secure');
  });

  it('strips Secure from logout cleanup cookies for approved local-stage admin origin', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    global.fetch = vi.fn().mockResolvedValue(
      new Response(null, {
        status: 204,
        headers: {
          'set-cookie': [
            'access_token=; Max-Age=0; Path=/api; HttpOnly; Secure; SameSite=Lax',
            'refresh_token=; Max-Age=0; Path=/api; HttpOnly; Secure; SameSite=Lax',
          ].join(', '),
        },
      }),
    ) as typeof fetch;

    const request = new NextRequest('http://127.0.0.1:13001/api/v1/auth/logout', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'http://127.0.0.1:13001',
      },
      body: JSON.stringify({}),
    });
    request.cookies.set('access_token', 'current-access');
    request.cookies.set('refresh_token', 'current-refresh');

    const response = await POST(request, createContext(['auth', 'logout']));
    const setCookieHeaders = readSetCookieHeaders(response).join('\n');

    expect(response.status).toBe(204);
    expect(setCookieHeaders).toContain('access_token=');
    expect(setCookieHeaders).toContain('refresh_token=');
    expect(setCookieHeaders).toContain('Max-Age=0');
    expect(setCookieHeaders).not.toContain('Secure');
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

    const request = new NextRequest('http://127.0.0.1:13001/api/v1/auth/logout', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'https://evil.example',
        referer: 'https://evil.example/admin-logout',
      },
      body: JSON.stringify({}),
    });

    const response = await POST(request, createContext(['auth', 'logout']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(headers.get('origin')).toBe('https://evil.example');
    expect(headers.get('referer')).toBe('https://evil.example/admin-logout');
    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual({ detail: 'CSRF origin validation failed' });
  });

  it('does not rewrite local-stage origins for production admin destinations', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal');
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'CSRF origin validation failed' }), {
        status: 403,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ) as typeof fetch;

    const request = new NextRequest('https://admin.cyber-vpn.net/api/v1/auth/logout', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'http://127.0.0.1:13001',
        referer: 'http://127.0.0.1:13001/en-EN/dashboard',
      },
      body: JSON.stringify({}),
    });

    const response = await POST(request, createContext(['auth', 'logout']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(headers.get('origin')).toBe('http://127.0.0.1:13001');
    expect(headers.get('referer')).toBe('http://127.0.0.1:13001/en-EN/dashboard');
    expect(response.status).toBe(403);
  });
});
