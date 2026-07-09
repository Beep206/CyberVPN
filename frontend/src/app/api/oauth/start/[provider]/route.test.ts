import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { NextRequest } from 'next/server';

import { GET } from './route';
import {
  OAUTH_TRANSACTION_COOKIE,
  parseProviderTransactionCookieValue,
} from '@/features/auth/lib/oauth-transaction';
import { OAUTH_PROVIDER_QUERY_PARAM } from '@/features/auth/lib/oauth-error-codes';

describe('GET /api/oauth/start/[provider]', () => {

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('redirects to provider authorize URL and stores signed transaction cookie', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          authorize_url: 'https://accounts.google.com/o/oauth2/v2/auth?state=csrf123',
        }),
        {
          status: 200,
          headers: {
            'content-type': 'application/json',
          },
        },
      ),
    ));

    const request = new NextRequest(
      'http://localhost:3000/api/oauth/start/google?locale=ru-RU&return_to=%2Fru-RU%2Fpricing',
      {
        headers: new Headers({
          'accept-language': 'ru-RU',
          'user-agent': 'Vitest',
          'x-forwarded-for': '1.2.3.4',
        }),
      },
    );

    const response = await GET(request, {
      params: Promise.resolve({ provider: 'google' }),
    });

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe(
      'https://accounts.google.com/o/oauth2/v2/auth?state=csrf123',
    );
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/oauth/google/login',
      expect.objectContaining({
        cache: 'no-store',
        method: 'GET',
      }),
    );
    const [, fetchInit] = vi.mocked(fetch).mock.calls[0] ?? [];
    const fetchHeaders = fetchInit?.headers as Headers;
    expect(fetchHeaders.get('x-forwarded-for')).toBeNull();
    expect(fetchHeaders.get('x-forwarded-host')).toBe('localhost:3000');
    expect(fetchHeaders.get('x-forwarded-proto')).toBe('http');

    const cookieValue = response.cookies.get(OAUTH_TRANSACTION_COOKIE)?.value;
    expect(cookieValue).toBeTruthy();
    expect(parseProviderTransactionCookieValue(cookieValue)).toEqual({
      locale: 'ru-RU',
      provider: 'google',
      returnTo: '/ru-RU/pricing',
    });
  });

  it('falls back to locale dashboard when return_to points to an auth page', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          authorize_url: 'https://github.com/login/oauth/authorize?state=csrf456',
        }),
        {
          status: 200,
          headers: {
            'content-type': 'application/json',
          },
        },
      ),
    ));

    const request = new NextRequest(
      'http://localhost:3000/api/oauth/start/github?locale=ru-RU&return_to=%2Fru-RU%2Flogin',
    );

    const response = await GET(request, {
      params: Promise.resolve({ provider: 'github' }),
    });

    const cookieValue = response.cookies.get(OAUTH_TRANSACTION_COOKIE)?.value;
    expect(parseProviderTransactionCookieValue(cookieValue)).toEqual({
      locale: 'ru-RU',
      provider: 'github',
      returnTo: '/ru-RU/dashboard',
    });
  });

  it('redirects upstream failures back to login with a stable provider-scoped error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 503 }),
    ));

    const request = new NextRequest(
      'http://localhost:3000/api/oauth/start/google?locale=ru-RU&return_to=%2Fru-RU%2Fdashboard',
    );

    const response = await GET(request, {
      params: Promise.resolve({ provider: 'google' }),
    });

    const location = new URL(response.headers.get('location') ?? 'http://localhost');
    expect(location.searchParams.get('oauth_error')).toBe('oauth_start_failed');
    expect(location.searchParams.get(OAUTH_PROVIDER_QUERY_PARAM)).toBe('google');
  });

  it('ignores allowlisted forwarded host headers when the browser-facing host is not trusted', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 503 }),
    ));

    const request = new NextRequest(
      'http://0.0.0.0:9001/api/oauth/start/google?locale=ru-RU&return_to=%2Fru-RU%2Fdashboard',
      {
        headers: new Headers({
          host: '0.0.0.0:9001',
          'x-forwarded-host': 'cyber-vpn.net',
          'x-forwarded-proto': 'https',
        }),
      },
    );

    const response = await GET(request, {
      params: Promise.resolve({ provider: 'google' }),
    });

    expect(response.headers.get('location')).toBe(
      'https://my.cyber-vpn.net/ru-RU/login?oauth_error=oauth_start_failed&oauth_provider=google',
    );
  });

  it('uses the browser-facing public host instead of an allowlisted spoofed forwarded host', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          authorize_url: 'https://accounts.google.com/o/oauth2/v2/auth?state=csrf123',
        }),
        {
          status: 200,
          headers: {
            'content-type': 'application/json',
          },
        },
      ),
    ));

    const request = new NextRequest(
      'https://my.cyber-vpn.net/api/oauth/start/google?locale=ru-RU',
      {
        headers: new Headers({
          host: 'my.cyber-vpn.net',
          'x-forwarded-host': 'localhost:3000',
          'x-forwarded-proto': 'http',
        }),
      },
    );

    await GET(request, {
      params: Promise.resolve({ provider: 'google' }),
    });

    const [, fetchInit] = vi.mocked(fetch).mock.calls[0] ?? [];
    const fetchHeaders = fetchInit?.headers as Headers;
    expect(fetchHeaders.get('x-forwarded-host')).toBe('my.cyber-vpn.net');
    expect(fetchHeaders.get('x-forwarded-proto')).toBe('https');
  });

  it('ignores untrusted forwarded host headers when building error redirects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 503 }),
    ));

    const request = new NextRequest(
      'http://0.0.0.0:9001/api/oauth/start/google?locale=ru-RU&return_to=%2Fru-RU%2Fdashboard',
      {
        headers: new Headers({
          host: '0.0.0.0:9001',
          'x-forwarded-host': 'evil.example',
          'x-forwarded-proto': 'http',
        }),
      },
    );

    const response = await GET(request, {
      params: Promise.resolve({ provider: 'google' }),
    });

    expect(response.headers.get('location')).toBe(
      'https://my.cyber-vpn.net/ru-RU/login?oauth_error=oauth_start_failed&oauth_provider=google',
    );
  });
});
