// @vitest-environment node

import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET, POST } from './route';
import { GET as GET_V3 } from '../../v3/[...path]/route';

const SET_COOKIE_BOUNDARY_NAMES = [
  '__Host-cvpn_device_id',
  '__Host-cvpn_private_catalog_session',
  'access_token',
  'customer_access_token',
  'customer_refresh_token',
  'cv_partner_attribution',
  'cv_ref_attribution',
  'partner_access_token',
  'partner_refresh_token',
  'refresh_token',
];

function createContext(path: string[]) {
  return {
    params: Promise.resolve({ path }),
  };
}

function getFetchInit() {
  return (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[1] as RequestInit;
}

function oversizedStreamingBody(): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      controller.enqueue(new Uint8Array(1_048_576));
      controller.enqueue(new Uint8Array(1));
      controller.close();
    },
  });
}

function readSetCookieHeaders(response: Response): string[] {
  const headers = response.headers as Headers & {
    getSetCookie?: () => string[];
  };

  if (typeof headers.getSetCookie === 'function') {
    return headers.getSetCookie().flatMap(splitSetCookieHeader);
  }

  const setCookie = response.headers.get('set-cookie');
  return setCookie ? splitSetCookieHeader(setCookie) : [];
}

function splitSetCookieHeader(headerValue: string): string[] {
  const cookies: string[] = [];
  let start = 0;

  for (let index = 0; index < headerValue.length; index += 1) {
    if (headerValue[index] !== ',') continue;

    const candidate = headerValue.slice(index + 1).trimStart();
    if (!SET_COOKIE_BOUNDARY_NAMES.some((name) => candidate.startsWith(`${name}=`))) {
      continue;
    }

    cookies.push(headerValue.slice(start, index).trim());
    start = index + 1;
  }

  cookies.push(headerValue.slice(start).trim());
  return cookies.filter(Boolean);
}

describe('admin API proxy route', () => {

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it('proxies browser API calls through the canonical admin host boundary', async () => {
    vi.stubEnv('API_INTERNAL_ORIGIN', 'http://backend.local');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ role: 'operator' }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
          'set-cookie': 'access_token=next; Path=/api; HttpOnly',
        },
      }),
    ));

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

  it('preserves canonical trailing slashes for backend collection roots', async () => {
    vi.stubEnv('API_INTERNAL_ORIGIN', 'http://backend.local');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ));

    const request = new NextRequest('http://admin.localhost:3001/api/v1/hosts/?limit=20');

    const response = await GET(request, createContext(['hosts']));

    expect(global.fetch).toHaveBeenCalledWith(
      'http://backend.local/api/v1/hosts/?limit=20',
      expect.objectContaining({
        method: 'GET',
        cache: 'no-store',
        redirect: 'manual',
      }),
    );
    expect(response.status).toBe(200);
  });

  it('does not forward browser-supplied internal service secret headers', async () => {
    vi.stubEnv('API_INTERNAL_ORIGIN', 'http://backend.local');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ role: 'operator' }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ));

    const request = new NextRequest('http://127.0.0.1:13001/api/v1/auth/session', {
      headers: {
        'x-backend-internal-secret': 'browser-backend-secret',
        'x-payment-settlement-worker-secret': 'browser-worker-secret',
        'x-telegram-bot-secret': 'browser-telegram-secret',
        'x-request-id': 'req-1',
      },
    });

    const response = await GET(request, createContext(['auth', 'session']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(headers.get('x-backend-internal-secret')).toBeNull();
    expect(headers.get('x-payment-settlement-worker-secret')).toBeNull();
    expect(headers.get('x-telegram-bot-secret')).toBeNull();
    expect(headers.get('x-request-id')).toBe('req-1');
    expect(response.status).toBe(200);
  });

  it('does not forward browser-supplied source IP or proxy identity headers', async () => {
    vi.stubEnv('API_INTERNAL_ORIGIN', 'http://backend.local');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ role: 'operator' }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ));

    const request = new NextRequest('http://127.0.0.1:13001/api/v1/admin/growth/status', {
      headers: {
        'cf-connecting-ip': '198.51.100.50',
        'fastly-client-ip': '198.51.100.51',
        forwarded: 'for=198.51.100.52;proto=https',
        'true-client-ip': '198.51.100.53',
        'x-client-ip': '198.51.100.54',
        'x-cluster-client-ip': '198.51.100.55',
        'x-forwarded-for': '198.51.100.56',
        'x-real-ip': '198.51.100.57',
        'x-request-id': 'req-source-ip',
      },
    });

    const response = await GET(request, createContext(['admin', 'growth', 'status']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(headers.get('cf-connecting-ip')).toBeNull();
    expect(headers.get('fastly-client-ip')).toBeNull();
    expect(headers.get('forwarded')).toBeNull();
    expect(headers.get('true-client-ip')).toBeNull();
    expect(headers.get('x-client-ip')).toBeNull();
    expect(headers.get('x-cluster-client-ip')).toBeNull();
    expect(headers.get('x-forwarded-for')).toBeNull();
    expect(headers.get('x-real-ip')).toBeNull();
    expect(headers.get('x-forwarded-host')).toBe('admin.cyber-vpn.net');
    expect(headers.get('x-forwarded-proto')).toBe('https');
    expect(headers.get('x-request-id')).toBe('req-source-ip');
    expect(response.status).toBe(200);
  });

  it('proxies v3 browser API calls through the same admin host boundary', async () => {
    vi.stubEnv('API_INTERNAL_ORIGIN', 'http://backend.local');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: 'healthy' }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ));

    const request = new NextRequest('http://127.0.0.1:13001/api/v3/admin/growth/fx/status', {
      headers: {
        'x-request-id': 'req-v3',
      },
    });
    request.cookies.set('access_token', 'current');

    const response = await GET_V3(request, createContext(['admin', 'growth', 'fx', 'status']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(global.fetch).toHaveBeenCalledWith(
      'http://backend.local/api/v3/admin/growth/fx/status',
      expect.objectContaining({
        method: 'GET',
        cache: 'no-store',
        redirect: 'manual',
      }),
    );
    expect(headers.get('x-forwarded-host')).toBe('admin.cyber-vpn.net');
    expect(headers.get('x-forwarded-proto')).toBe('https');
    expect(headers.get('cookie')).toBe('access_token=current');
    expect(headers.get('x-request-id')).toBe('req-v3');
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ status: 'healthy' });
  });

  it('forwards mutating request bodies with canonical realm and CSRF headers for approved local-stage admin', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ));

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

  it('rejects oversized mutating requests from content-length before forwarding upstream', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ));

    const request = new NextRequest('http://127.0.0.1:13001/api/v1/auth/logout', {
      method: 'POST',
      headers: {
        'content-length': '1048577',
        'content-type': 'application/json',
      },
      body: '{}',
    });

    const response = await POST(request, createContext(['auth', 'logout']));

    expect(global.fetch).not.toHaveBeenCalled();
    expect(response.status).toBe(413);
    await expect(response.json()).resolves.toEqual({
      detail: {
        code: 'REQUEST_BODY_TOO_LARGE',
        message: 'Request body is too large.',
      },
    });
  });

  it('rejects oversized chunked mutating requests without content-length before forwarding upstream', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ));

    const request = new NextRequest('http://127.0.0.1:13001/api/v1/auth/logout', {
      method: 'POST',
      headers: {
        'content-type': 'application/octet-stream',
      },
      body: oversizedStreamingBody(),
      duplex: 'half',
    } as unknown as ConstructorParameters<typeof NextRequest>[1]);

    const response = await POST(request, createContext(['auth', 'logout']));

    expect(global.fetch).not.toHaveBeenCalled();
    expect(response.status).toBe(413);
  });

  it('canonicalizes approved local-stage source headers when served on the container port', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ));

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
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ));

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

  it('canonicalizes admin.localhost dev origins for backend CSRF allowlists', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ));

    const request = new NextRequest('http://admin.localhost:3001/api/v1/auth/logout', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'http://admin.localhost:3001',
        referer: 'http://admin.localhost:3001/ru-RU/dashboard',
      },
      body: JSON.stringify({}),
    });

    const response = await POST(request, createContext(['auth', 'logout']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(headers.get('origin')).toBe('https://admin.cyber-vpn.net');
    expect(headers.get('referer')).toBe('https://admin.cyber-vpn.net/ru-RU/dashboard');
    expect(response.status).toBe(204);
  });


  it('preserves local-stage Origin and Referer for passkey WebAuthn ceremonies', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ challengeId: 'synthetic-challenge' }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ));

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

  it('preserves admin.localhost dev Origin and Referer for passkey WebAuthn ceremonies', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ challengeId: 'synthetic-challenge' }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ));

    const request = new NextRequest('http://admin.localhost:3001/api/v1/auth/passkeys/registration/options', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'http://admin.localhost:3001',
        referer: 'http://admin.localhost:3001/ru-RU/security/passkeys',
      },
      body: JSON.stringify({ label: 'AC-18 admin.localhost synthetic' }),
    });

    const response = await POST(request, createContext(['auth', 'passkeys', 'registration', 'options']));
    const init = getFetchInit();
    const headers = init.headers as Headers;

    expect(headers.get('x-forwarded-host')).toBe('admin.cyber-vpn.net');
    expect(headers.get('x-forwarded-proto')).toBe('https');
    expect(headers.get('origin')).toBe('http://admin.localhost:3001');
    expect(headers.get('referer')).toBe('http://admin.localhost:3001/ru-RU/security/passkeys');
    expect(response.status).toBe(200);
  });

  it('strips Secure from passkey auth cookies for approved local-stage admin origin', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ requires_2fa: false }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
          'set-cookie': 'access_token=backend_access; Path=/api; HttpOnly; Secure; SameSite=Lax',
        },
      }),
    ));

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
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, {
        status: 204,
        headers: {
          'set-cookie': [
            'access_token=; Expires=Wed, 21 Oct 2037 07:28:00 GMT; Max-Age=0; Path=/api/a,b=c; HttpOnly; Secure; SameSite=Lax',
            'refresh_token=; Max-Age=0; Path=/api; HttpOnly; Secure; SameSite=Lax',
          ].join(', '),
        },
      }),
    ));

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
    const setCookieHeadersList = readSetCookieHeaders(response);
    const setCookieHeaders = setCookieHeadersList.join('\n');

    expect(response.status).toBe(204);
    expect(setCookieHeadersList).toHaveLength(2);
    expect(setCookieHeaders).toContain('access_token=');
    expect(setCookieHeaders).toContain('Path=/api/a,b=c');
    expect(setCookieHeaders).toContain('refresh_token=');
    expect(setCookieHeaders).toContain('Max-Age=0');
    expect(setCookieHeaders).not.toContain('Secure');
  });

  it('preserves foreign origins so backend CSRF can reject cross-site cookie requests', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'CSRF origin validation failed' }), {
        status: 403,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ));

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
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'CSRF origin validation failed' }), {
        status: 403,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ));

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
