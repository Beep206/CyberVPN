// @vitest-environment node

import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET, POST } from './route';

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

describe('partner API proxy route', () => {

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it('proxies browser API calls through the canonical partner host boundary', async () => {
    vi.stubEnv('API_INTERNAL_ORIGIN', 'http://backend.local');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ auth_realm_key: 'partner' }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
          'set-cookie': 'partner_access_token=next; Path=/api; HttpOnly',
        },
      }),
    ));

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

    const request = new NextRequest('http://portal.localhost:3002/api/v1/partner-payout-accounts/?limit=20');

    const response = await GET(request, createContext(['partner-payout-accounts']));

    expect(global.fetch).toHaveBeenCalledWith(
      'http://backend.local/api/v1/partner-payout-accounts/?limit=20',
      expect.objectContaining({
        method: 'GET',
        cache: 'no-store',
        redirect: 'manual',
      }),
    );
    expect(response.status).toBe(200);
  });

  it('preserves multiple upstream auth Set-Cookie headers', async () => {
    vi.stubEnv('API_INTERNAL_ORIGIN', 'http://backend.local');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ auth_realm_key: 'partner' }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
          'set-cookie': [
            'partner_access_token=next; Expires=Wed, 21 Oct 2037 07:28:00 GMT; Path=/api/a,b=c; HttpOnly; SameSite=Lax',
            'partner_refresh_token=refresh; Path=/api; HttpOnly; SameSite=Lax',
          ].join(', '),
        },
      }),
    ));

    const request = new NextRequest('http://portal.localhost:3004/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: 'http://portal.localhost:3004',
      },
      body: JSON.stringify({ login_or_email: 'partner@example.test', password: 'redacted' }),
    });

    const response = await POST(request, createContext(['auth', 'login']));
    const setCookieHeaders = readSetCookieHeaders(response);

    expect(response.status).toBe(200);
    expect(setCookieHeaders).toHaveLength(2);
    expect(setCookieHeaders[0]).toContain('partner_access_token=next');
    expect(setCookieHeaders[0]).toContain('Path=/api/a,b=c');
    expect(setCookieHeaders[1]).toContain('partner_refresh_token=refresh');
  });

  it('forwards mutating request bodies with canonical partner CSRF headers for approved local-stage origins', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ));

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

  it('rejects oversized mutating requests from content-length before forwarding upstream', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal/');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    ));

    const request = new NextRequest('http://portal.localhost:3004/api/v1/auth/logout', {
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

    const request = new NextRequest('http://portal.localhost:3004/api/v1/auth/logout', {
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

  it('does not forward attacker-controlled unknown forwarded hosts to backend realm resolution', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ));

    const request = new NextRequest('http://portal.localhost:3004/api/v1/auth/session', {
      headers: {
        'x-forwarded-host': 'evil.example',
        'x-auth-realm': 'admin',
      },
    });

    const response = await GET(request, createContext(['auth', 'session']));
    const headers = getFetchInit().headers as Headers;

    expect(headers.get('x-forwarded-host')).toBe('portal.localhost:3004');
    expect(headers.get('x-forwarded-host')).not.toBe('evil.example');
    expect(headers.get('x-auth-realm')).toBeNull();
    expect(response.status).toBe(200);
  });

  it('does not forward browser-supplied internal service credentials', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ));

    const request = new NextRequest('http://portal.localhost:3004/api/v1/subscriptions/retry-provisioning', {
      method: 'POST',
      headers: {
        authorization: 'Bearer browser-supplied',
        'content-type': 'application/json',
        origin: 'http://portal.localhost:3004',
        'x-backend-internal-secret': 'leaked-backend-secret',
        'x-payment-settlement-worker-secret': 'leaked-payment-secret',
        'x-request-id': 'req-allowlisted',
        'x-telegram-bot-secret': 'leaked-telegram-secret',
      },
      body: JSON.stringify({ subscription_id: 'sub_123' }),
    });

    const response = await POST(request, createContext(['subscriptions', 'retry-provisioning']));
    const headers = getFetchInit().headers as Headers;

    expect(headers.get('authorization')).toBeNull();
    expect(headers.get('x-backend-internal-secret')).toBeNull();
    expect(headers.get('x-payment-settlement-worker-secret')).toBeNull();
    expect(headers.get('x-telegram-bot-secret')).toBeNull();
    expect(headers.get('x-request-id')).toBe('req-allowlisted');
    expect(headers.get('content-type')).toBe('application/json');
    expect(response.status).toBe(200);
  });

  it('rejects unknown request hosts before forwarding to the backend', async () => {
    vi.stubEnv('API_URL', 'http://backend.internal');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
        },
      }),
    ));

    const request = new NextRequest('https://unknown.example/api/v1/auth/session', {
      headers: {
        'x-forwarded-host': 'admin.cyber-vpn.net',
      },
    });

    const response = await GET(request, createContext(['auth', 'session']));

    expect(global.fetch).not.toHaveBeenCalled();
    expect(response.status).toBe(421);
    await expect(response.json()).resolves.toEqual({
      detail: {
        code: 'UNKNOWN_PARTNER_SURFACE_HOST',
        message: 'Unknown partner surface host.',
      },
    });
  });
});
