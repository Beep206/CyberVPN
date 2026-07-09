// @vitest-environment node

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET, POST } from './route';

function createContext(path: string[]) {
  return {
    params: Promise.resolve({ path }),
  };
}

function getFetchCalls() {
  return (global.fetch as ReturnType<typeof vi.fn>).mock.calls;
}

function getFetchHeaders(callIndex: number): Headers {
  const init = getFetchCalls()[callIndex]?.[1] as RequestInit | undefined;
  return new Headers(init?.headers);
}

describe('admin Telegram bot integration BFF route', () => {
  beforeEach(() => {
    vi.stubEnv('API_INTERNAL_ORIGIN', 'http://backend.local');
    vi.stubEnv('API_URL', 'http://public-backend.local');
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://public-next-backend.local');
    vi.stubEnv('TELEGRAM_BOT_INTERNAL_SECRET', 'test-telegram-internal-secret');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it('authenticates the admin session before proxying with the server-side Telegram secret', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ realm: 'admin' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ enabled: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })));

    const request = new NextRequest(
      'http://admin.localhost:3001/api/integrations/telegram/bot/settings/access?region=ru',
      {
        headers: {
          cookie: 'access_token=current; refresh_token=refresh',
          'x-forwarded-for': '203.0.113.9',
          'x-backend-internal-secret': 'browser-backend-secret',
          'x-telegram-bot-secret': 'browser-telegram-secret',
          'x-request-id': 'req-telegram',
          'user-agent': 'vitest',
          'accept-language': 'ru-RU',
        },
      },
    );

    const response = await GET(request, createContext(['settings', 'access']));
    const sessionHeaders = getFetchHeaders(0);
    const proxyHeaders = getFetchHeaders(1);

    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      'http://backend.local/api/v1/auth/session',
      expect.objectContaining({
        method: 'GET',
        cache: 'no-store',
      }),
    );
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      new URL('http://backend.local/api/v1/telegram/bot/settings/access?region=ru'),
      expect.objectContaining({
        method: 'GET',
        cache: 'no-store',
      }),
    );
    expect(sessionHeaders.get('cookie')).toBe('access_token=current; refresh_token=refresh');
    expect(sessionHeaders.get('x-forwarded-for')).toBeNull();
    expect(sessionHeaders.get('x-backend-internal-secret')).toBeNull();
    expect(sessionHeaders.get('x-telegram-bot-secret')).toBeNull();
    expect(sessionHeaders.get('x-request-id')).toBe('req-telegram');
    expect(sessionHeaders.get('x-forwarded-host')).toBe('admin.cyber-vpn.net');
    expect(sessionHeaders.get('x-forwarded-proto')).toBe('https');
    expect(proxyHeaders.get('x-telegram-bot-secret')).toBe('test-telegram-internal-secret');
    expect(proxyHeaders.get('x-forwarded-for')).toBeNull();
    expect(proxyHeaders.get('x-backend-internal-secret')).toBeNull();
    expect(proxyHeaders.get('x-request-id')).toBe('req-telegram');
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ enabled: true });
  });

  it('does not call the Telegram upstream when the admin session is not authenticated', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Unauthorized' }), {
        status: 401,
        headers: { 'content-type': 'application/json' },
      }),
    ));

    const request = new NextRequest(
      'http://admin.localhost:3001/api/integrations/telegram/bot/settings/access',
      { headers: { cookie: 'access_token=expired' } },
    );

    const response = await GET(request, createContext(['settings', 'access']));

    expect(response.status).toBe(401);
    expect(global.fetch).toHaveBeenCalledTimes(1);
    await expect(response.json()).resolves.toEqual({ detail: 'Not authenticated.' });
  });

  it('fails closed when the server-side Telegram secret is not configured', async () => {
    vi.stubEnv('TELEGRAM_BOT_INTERNAL_SECRET', '');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ realm: 'admin' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    ));

    const request = new NextRequest(
      'http://admin.localhost:3001/api/integrations/telegram/bot/plans',
      { headers: { cookie: 'access_token=current' } },
    );

    const response = await GET(request, createContext(['plans']));

    expect(response.status).toBe(503);
    expect(global.fetch).toHaveBeenCalledTimes(1);
    await expect(response.json()).resolves.toEqual({
      detail: 'TELEGRAM_BOT_INTERNAL_SECRET is not configured.',
    });
  });

  it('forwards mutating JSON bodies only after session and secret checks pass', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ realm: 'admin' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ saved: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })));

    const request = new NextRequest(
      'http://admin.localhost:3001/api/integrations/telegram/bot/settings/access',
      {
        method: 'POST',
        headers: {
          cookie: 'access_token=current',
          'content-type': 'application/json',
        },
        body: JSON.stringify({ adminAccessEnabled: true }),
      },
    );

    const response = await POST(request, createContext(['settings', 'access']));
    const init = getFetchCalls()[1]?.[1] as RequestInit;
    const proxyHeaders = getFetchHeaders(1);

    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      new URL('http://backend.local/api/v1/telegram/bot/settings/access'),
      expect.objectContaining({
        method: 'POST',
        cache: 'no-store',
      }),
    );
    expect(init.body).toBe(JSON.stringify({ adminAccessEnabled: true }));
    expect(proxyHeaders.get('content-type')).toBe('application/json');
    expect(proxyHeaders.get('x-telegram-bot-secret')).toBe('test-telegram-internal-secret');
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ saved: true });
  });
});
