import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { connectionMock } = vi.hoisted(() => ({
  connectionMock: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('next/server', async (importOriginal) => {
  const actual = await importOriginal<typeof import('next/server')>();
  return {
    ...actual,
    connection: connectionMock,
  };
});

import { GET } from './route';

const ORIGINAL_API_URL = process.env.API_URL;
const ORIGINAL_NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL;

function createRequest(cookie = 'customer_access_token=token'): unknown {
  return {
    headers: new Headers({
      cookie,
      host: 'my.cyber-vpn.net',
      'x-forwarded-for': '203.0.113.10',
      'x-request-id': 'req-test',
    }),
    nextUrl: {
      host: 'my.cyber-vpn.net',
      protocol: 'https:',
    },
  };
}

describe('GET /api/auth/optional-session', () => {
  beforeEach(() => {
    process.env.API_URL = 'https://backend.internal';
    process.env.NEXT_PUBLIC_API_URL = '';
    connectionMock.mockClear();
    vi.stubGlobal('fetch', vi.fn<typeof fetch>());
  });

  afterEach(() => {
    process.env.API_URL = ORIGINAL_API_URL;
    process.env.NEXT_PUBLIC_API_URL = ORIGINAL_NEXT_PUBLIC_API_URL;
    vi.unstubAllGlobals();
  });

  it('forwards cookies to backend session and returns the user when authenticated', async () => {
    const user = {
      id: 'user-1',
      email: 'user@example.com',
      role: 'viewer',
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
    expect(headers.get('x-forwarded-host')).toBe('my.cyber-vpn.net');
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
    process.env.API_URL = '';
    process.env.NEXT_PUBLIC_API_URL = '';

    const response = await GET(createRequest() as never);

    expect(response.status).toBe(200);
    expect(await response.json()).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });
});
