import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { POST } from './route';
import {
  createPendingTwoFactorCookieValue,
  PENDING_2FA_COOKIE,
} from '@/features/auth/lib/pending-twofa';

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

function responseWithSetCookie(
  body: unknown,
  setCookie: string,
): Response {
  const response = new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  });

  Object.defineProperty(response.headers, 'getSetCookie', {
    configurable: true,
    value: () => [setCookie],
  });

  return response;
}

function responseWithCollapsedSetCookie(
  body: unknown,
  setCookie: string,
): Response {
  const response = new Response(JSON.stringify(body), {
    status: 200,
    headers: {
      'content-type': 'application/json',
    },
  });

  Object.defineProperty(response.headers, 'getSetCookie', {
    configurable: true,
    value: () => [setCookie],
  });

  return response;
}

describe('POST /api/auth/2fa/complete', () => {

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('completes pending 2FA, forwards backend cookies, and returns redirect target', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      responseWithSetCookie(
        {
          access_token: 'access_token_value',
          refresh_token: 'refresh_token_value',
          token_type: 'bearer',
          expires_in: 3600,
        },
        'access_token=abc; Path=/; HttpOnly',
      ),
    ));

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'ru-RU',
      '/ru-RU/dashboard',
      true,
    );
    const request = new NextRequest('http://localhost:3000/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '123456' }),
      headers: {
        'content-type': 'application/json',
        'x-forwarded-for': '203.0.113.55',
        'x-forwarded-host': 'evil.example',
        'x-forwarded-proto': 'http',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/2fa/complete',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ code: '123456' }),
        cache: 'no-store',
        headers: expect.any(Headers),
      }),
    );
    const [, fetchInit] = vi.mocked(fetch).mock.calls[0] ?? [];
    const fetchHeaders = fetchInit?.headers as Headers;
    expect(fetchHeaders.get('x-forwarded-for')).toBeNull();
    expect(fetchHeaders.get('x-forwarded-host')).toBe('localhost:3000');
    expect(fetchHeaders.get('x-forwarded-proto')).toBe('http');
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      redirect_to: '/ru-RU/dashboard?welcome=true',
    });
    expect(readSetCookieHeaders(response).join('\n')).toContain('access_token=abc');
  });

  it('splits collapsed backend auth cookies without corrupting comma attributes', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      responseWithCollapsedSetCookie(
        {
          access_token: 'access_token_value',
          refresh_token: 'refresh_token_value',
          token_type: 'bearer',
          expires_in: 3600,
        },
        [
          'customer_access_token=access; Path=/api; Expires=Wed, 21 Oct 2037 07:28:00 GMT; HttpOnly; SameSite=Lax',
          'customer_refresh_token=refresh; Path=/api/a,b=c; HttpOnly; SameSite=Lax',
          '__Host-cvpn_device_id=device; Path=/; Secure; HttpOnly; SameSite=Lax',
        ].join(', '),
      ),
    ));

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'en-EN',
      '/en-EN/dashboard',
      false,
    );
    const request = new NextRequest('https://my.cyber-vpn.net/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '123456' }),
      headers: {
        'content-type': 'application/json',
        host: 'my.cyber-vpn.net',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);

    expect(response.status).toBe(200);
    const setCookieHeaders = readSetCookieHeaders(response);
    expect(setCookieHeaders).toEqual(
      expect.arrayContaining([
        expect.stringContaining('customer_access_token=access'),
        expect.stringContaining('customer_refresh_token=refresh'),
        expect.stringContaining('__Host-cvpn_device_id=device'),
      ]),
    );
    expect(setCookieHeaders.some((header) => header.startsWith('b=c'))).toBe(false);
  });

  it('falls back to the canonical host when no trusted local or public host exists', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      responseWithSetCookie(
        {
          access_token: 'access_token_value',
          refresh_token: 'refresh_token_value',
          token_type: 'bearer',
          expires_in: 3600,
        },
        'access_token=abc; Path=/; HttpOnly',
      ),
    ));

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'ru-RU',
      '/ru-RU/dashboard',
      false,
    );
    const request = new NextRequest('http://0.0.0.0:9001/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '123456' }),
      headers: {
        'content-type': 'application/json',
        host: '0.0.0.0:9001',
        'x-forwarded-for': '203.0.113.55',
        'x-forwarded-host': 'evil.example',
        'x-forwarded-proto': 'http',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);

    expect(response.status).toBe(200);
    const [, fetchInit] = vi.mocked(fetch).mock.calls[0] ?? [];
    const fetchHeaders = fetchInit?.headers as Headers;
    expect(fetchHeaders.get('x-forwarded-for')).toBeNull();
    expect(fetchHeaders.get('x-forwarded-host')).toBe('my.cyber-vpn.net');
    expect(fetchHeaders.get('x-forwarded-proto')).toBe('https');
  });

  it('uses the browser-facing public host instead of an allowlisted spoofed forwarded host', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      responseWithSetCookie(
        {
          access_token: 'access_token_value',
          refresh_token: 'refresh_token_value',
          token_type: 'bearer',
          expires_in: 3600,
        },
        'access_token=abc; Path=/; HttpOnly',
      ),
    ));

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'ru-RU',
      '/ru-RU/dashboard',
      false,
    );
    const request = new NextRequest('https://my.cyber-vpn.net/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '123456' }),
      headers: {
        'content-type': 'application/json',
        host: 'my.cyber-vpn.net',
        'x-forwarded-host': 'localhost:3000',
        'x-forwarded-proto': 'http',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);

    expect(response.status).toBe(200);
    const [, fetchInit] = vi.mocked(fetch).mock.calls[0] ?? [];
    const fetchHeaders = fetchInit?.headers as Headers;
    expect(fetchHeaders.get('x-forwarded-host')).toBe('my.cyber-vpn.net');
    expect(fetchHeaders.get('x-forwarded-proto')).toBe('https');
  });

  it('rejects requests without a valid pending 2FA cookie', async () => {
    const request = new NextRequest('http://localhost:3000/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '123456' }),
      headers: {
        'content-type': 'application/json',
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({
      detail: 'Two-factor login session expired. Start sign-in again.',
    });
  });
});
