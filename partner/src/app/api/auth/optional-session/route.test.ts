import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { connectionMock } = vi.hoisted(() => ({
  connectionMock: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('next/server', () => ({
  connection: connectionMock,
  NextResponse: {
    json: (body: unknown, init?: ResponseInit) => Response.json(body, init),
  },
}));

import { GET } from './route';

const ORIGINAL_API_INTERNAL_ORIGIN = process.env.API_INTERNAL_ORIGIN;
const ORIGINAL_API_URL = process.env.API_URL;
const ORIGINAL_NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL;

function createRequest(
  cookie = 'customer_access_token=token',
  host = 'storefront.localhost:3002',
  forwardedHost = 'evil.example',
): unknown {
  return {
    headers: new Headers({
      cookie,
      host,
      'x-forwarded-host': forwardedHost,
      'x-forwarded-for': '203.0.113.10',
      'x-request-id': 'req-test',
    }),
    nextUrl: {
      host,
      protocol: 'http:',
    },
  };
}

describe('GET /api/auth/optional-session', () => {
  beforeEach(() => {
    process.env.API_INTERNAL_ORIGIN = 'https://backend.internal';
    process.env.API_URL = '';
    process.env.NEXT_PUBLIC_API_URL = '';
    connectionMock.mockClear();
    vi.stubGlobal('fetch', vi.fn<typeof fetch>());
  });

  afterEach(() => {
    process.env.API_INTERNAL_ORIGIN = ORIGINAL_API_INTERNAL_ORIGIN;
    process.env.API_URL = ORIGINAL_API_URL;
    process.env.NEXT_PUBLIC_API_URL = ORIGINAL_NEXT_PUBLIC_API_URL;
    vi.unstubAllGlobals();
  });

  it('forwards customer cookies to backend session using the canonical storefront host', async () => {
    const user = {
      id: 'user-1',
      email: 'user@example.com',
      role: 'user',
      is_active: true,
      is_email_verified: true,
      created_at: '2026-05-29T00:00:00.000Z',
    };
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(user), {
      headers: { 'content-type': 'application/json' },
      status: 200,
    }));

    const response = await GET(createRequest() as never);

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(user);
    expect(connectionMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith(
      'https://backend.internal/api/v1/auth/session',
      expect.objectContaining({
        cache: 'no-store',
        method: 'GET',
      }),
    );
    const [, init] = fetchMock.mock.calls[0] ?? [];
    const headers = init?.headers as Headers;
    expect(headers.get('cookie')).toBe('customer_access_token=token');
    expect(headers.get('x-forwarded-host')).toBe('storefront.localhost:3002');
    expect(headers.get('x-forwarded-proto')).toBe('https');
    expect(headers.get('x-forwarded-for')).toBeNull();
  });

  it('uses the browser-facing partner host instead of a spoofed forwarded host', async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(null), {
      headers: { 'content-type': 'application/json' },
      status: 200,
    }));

    const response = await GET(createRequest('customer_access_token=token', 'portal.localhost:3002', 'localhost:3000') as never);

    expect(response.status).toBe(200);
    const [, init] = fetchMock.mock.calls[0] ?? [];
    const headers = init?.headers as Headers;
    expect(headers.get('x-forwarded-host')).toBe('portal.localhost:3002');
    expect(headers.get('x-forwarded-proto')).toBe('https');
  });

  it('returns empty 200 for anonymous backend session without surfacing a browser 401', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Unauthorized' }), {
      status: 401,
    }));

    const response = await GET(createRequest('') as never);

    expect(response.status).toBe(200);
    expect(response.headers.get('Cache-Control')).toBe('no-store');
    expect(await response.json()).toBeNull();
  });

  it('returns empty 200 when backend configuration or upstream is unavailable', async () => {
    process.env.API_INTERNAL_ORIGIN = '';
    process.env.API_URL = '';
    process.env.NEXT_PUBLIC_API_URL = '';

    const response = await GET(createRequest() as never);

    expect(response.status).toBe(200);
    expect(await response.json()).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('rejects unknown partner surface hosts before forwarding cookies', async () => {
    const response = await GET(createRequest('customer_access_token=token', 'evil.example') as never);

    expect(response.status).toBe(421);
    expect(await response.json()).toEqual({
      detail: { code: 'UNKNOWN_PARTNER_SURFACE_HOST', message: 'Unknown partner surface host.' },
    });
    expect(fetch).not.toHaveBeenCalled();
  });
});
