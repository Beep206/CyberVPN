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

describe('POST /api/auth/2fa/complete', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.unstubAllEnvs();
  });

  it('completes pending 2FA, forwards backend cookies, and returns redirect target', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        getSetCookie: () => ['access_token=abc; Path=/; HttpOnly'],
        get: (name: string) =>
          name.toLowerCase() === 'set-cookie'
            ? 'access_token=abc; Path=/; HttpOnly'
            : null,
      },
      json: async () => ({
          access_token: 'access_token_value',
          refresh_token: 'refresh_token_value',
          token_type: 'bearer',
          expires_in: 3600,
        }),
    } as unknown as Response) as typeof fetch;

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'ru-RU',
      '/ru-RU/dashboard',
      true,
    );
    const request = new NextRequest('http://localhost:3002/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '123456' }),
      headers: {
        'content-type': 'application/json',
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
    const [, options] = vi.mocked(global.fetch).mock.calls[0];
    const headers = options?.headers as Headers;
    expect(headers.get('x-auth-realm')).toBe('partner');
    expect(headers.get('x-forwarded-host')).toBe('partner.cyber-vpn.net');
    expect(headers.get('x-forwarded-proto')).toBe('https');
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      redirect_to: '/ru-RU/dashboard?welcome=true',
    });
    expect(readSetCookieHeaders(response).join('\n')).toContain('access_token=abc');
  });

  it('splits combined backend Set-Cookie fallback headers before forwarding to the browser', async () => {
    const combinedSetCookie = [
      'partner_access_token=access; Path=/api; Max-Age=900; Expires=Thu, 04 Jun 2026 17:15:00 GMT; HttpOnly; SameSite=Lax',
      'partner_refresh_token=refresh; Path=/api; Max-Age=604800; Expires=Thu, 11 Jun 2026 17:00:00 GMT; HttpOnly; SameSite=Lax',
    ].join(', ');

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        get: (name: string) =>
          name.toLowerCase() === 'set-cookie'
            ? combinedSetCookie
            : null,
      },
      json: async () => ({
        access_token: 'access_token_value',
        refresh_token: 'refresh_token_value',
        token_type: 'bearer',
        expires_in: 3600,
      }),
    } as unknown as Response) as typeof fetch;

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'en-EN',
      '/en-EN/dashboard',
      false,
    );
    const request = new NextRequest('http://portal.localhost:3004/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '654321' }),
      headers: {
        'content-type': 'application/json',
        host: 'portal.localhost:3004',
        'x-forwarded-host': 'portal.localhost:3004',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);
    const setCookieHeaders = readSetCookieHeaders(response);

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      redirect_to: '/en-EN/dashboard',
    });
    expect(setCookieHeaders).toEqual(
      expect.arrayContaining([
        expect.stringContaining('partner_access_token=access'),
        expect.stringContaining('partner_refresh_token=refresh'),
      ]),
    );
    expect(setCookieHeaders.find((header) => header.includes('partner_access_token')))
      .not.toContain('partner_refresh_token=refresh');
  });

  it('strips incompatible Domain and Secure for approved local partner HTTP Set-Cookie headers', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        getSetCookie: () => [
          'partner_access_token=access; Domain=cyber-vpn.net; Path=/api; Max-Age=900; Expires=Thu, 04 Jun 2026 17:15:00 GMT; HttpOnly; Secure; SameSite=Lax',
          'partner_refresh_token=refresh; Domain=cyber-vpn.net; Path=/api; Max-Age=604800; HttpOnly; Secure; SameSite=Lax',
        ],
        get: () => null,
      },
      json: async () => ({ redirect_to: '/en-EN/dashboard' }),
    } as unknown as Response) as typeof fetch;

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'en-EN',
      '/en-EN/dashboard',
      false,
    );
    const request = new NextRequest('http://portal.localhost:3004/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '654321' }),
      headers: {
        'content-type': 'application/json',
        host: 'portal.localhost:3004',
        'x-forwarded-host': 'portal.localhost:3004',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);
    const setCookieHeaders = readSetCookieHeaders(response).join('\n');

    expect(response.status).toBe(200);
    expect(setCookieHeaders).toContain('partner_access_token=access');
    expect(setCookieHeaders).toContain('partner_refresh_token=refresh');
    expect(setCookieHeaders).not.toContain('Domain=cyber-vpn.net');
    expect(setCookieHeaders).toContain('Path=/api');
    expect(setCookieHeaders).toContain('Max-Age=900');
    expect(setCookieHeaders).toContain('Expires=Thu, 04 Jun 2026 17:15:00 GMT');
    expect(setCookieHeaders).toContain('HttpOnly');
    expect(setCookieHeaders).not.toContain('Secure');
    expect(setCookieHeaders).toContain('SameSite=Lax');
  });

  it('preserves Secure Set-Cookie attributes for production partner portal requests', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        getSetCookie: () => [
          'partner_access_token=access; Domain=cyber-vpn.net; Path=/api; Max-Age=900; HttpOnly; Secure; SameSite=Lax',
        ],
        get: () => null,
      },
      json: async () => ({}),
    } as unknown as Response) as typeof fetch;

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'en-EN',
      '/en-EN/dashboard',
      false,
    );
    const request = new NextRequest('https://partner.cyber-vpn.net/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '654321' }),
      headers: {
        'content-type': 'application/json',
        host: 'partner.cyber-vpn.net',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);
    const setCookieHeaders = readSetCookieHeaders(response).join('\n');

    expect(response.status).toBe(200);
    expect(setCookieHeaders).toContain('Domain=cyber-vpn.net');
    expect(setCookieHeaders).toContain('Secure');
  });

  it('preserves compatible backend Set-Cookie Domain values while stripping local Secure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        getSetCookie: () => [
          'partner_access_token=access; Domain=.localhost; Path=/api; Max-Age=900; Expires=Thu, 04 Jun 2026 17:15:00 GMT; HttpOnly; Secure; SameSite=Lax',
        ],
        get: () => null,
      },
      json: async () => ({}),
    } as unknown as Response) as typeof fetch;

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'en-EN',
      '/en-EN/dashboard',
      false,
    );
    const request = new NextRequest('http://portal.localhost:3004/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '654321' }),
      headers: {
        'content-type': 'application/json',
        host: 'portal.localhost:3004',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);
    const setCookieHeaders = readSetCookieHeaders(response).join('\n');

    expect(response.status).toBe(200);
    expect(setCookieHeaders).toContain('Domain=.localhost');
    expect(setCookieHeaders).toContain('Path=/api');
    expect(setCookieHeaders).toContain('Max-Age=900');
    expect(setCookieHeaders).toContain('Expires=Thu, 04 Jun 2026 17:15:00 GMT');
    expect(setCookieHeaders).toContain('HttpOnly');
    expect(setCookieHeaders).not.toContain('Secure');
    expect(setCookieHeaders).toContain('SameSite=Lax');
  });

  it('strips Secure for approved storefront local HTTP hosts', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        getSetCookie: () => [
          'partner_access_token=access; Path=/api; HttpOnly; Secure; SameSite=Lax',
        ],
        get: () => null,
      },
      json: async () => ({}),
    } as unknown as Response) as typeof fetch;

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'en-EN',
      '/en-EN/dashboard',
      false,
    );
    const request = new NextRequest('http://storefront.localhost:3004/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '654321' }),
      headers: {
        'content-type': 'application/json',
        host: 'storefront.localhost:3004',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);
    const setCookieHeaders = readSetCookieHeaders(response).join('\n');

    expect(response.status).toBe(200);
    expect(setCookieHeaders).toContain('partner_access_token=access');
    expect(setCookieHeaders).toContain('Path=/api');
    expect(setCookieHeaders).toContain('HttpOnly');
    expect(setCookieHeaders).not.toContain('Secure');
    expect(setCookieHeaders).toContain('SameSite=Lax');
  });

  it('preserves Secure for non-approved HTTP hosts', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        getSetCookie: () => [
          'partner_access_token=access; Path=/api; HttpOnly; Secure; SameSite=Lax',
        ],
        get: () => null,
      },
      json: async () => ({}),
    } as unknown as Response) as typeof fetch;

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'en-EN',
      '/en-EN/dashboard',
      false,
    );
    const request = new NextRequest('http://example.localhost:3004/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '654321' }),
      headers: {
        'content-type': 'application/json',
        host: 'example.localhost:3004',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);
    const setCookieHeaders = readSetCookieHeaders(response).join('\n');

    expect(response.status).toBe(200);
    expect(setCookieHeaders).toContain('Secure');
  });

  it('preserves Secure for approved local HTTP hosts when running in production mode', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('PENDING_2FA_SECRET', 'test-only-production-pending-two-factor-secret');
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        getSetCookie: () => [
          'partner_access_token=access; Path=/api; HttpOnly; Secure; SameSite=Lax',
        ],
        get: () => null,
      },
      json: async () => ({}),
    } as unknown as Response) as typeof fetch;

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'en-EN',
      '/en-EN/dashboard',
      false,
    );
    const request = new NextRequest('http://portal.localhost:3004/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '654321' }),
      headers: {
        'content-type': 'application/json',
        host: 'portal.localhost:3004',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);
    const setCookieHeaders = readSetCookieHeaders(response).join('\n');

    expect(response.status).toBe(200);
    expect(setCookieHeaders).toContain('Secure');
  });

  it('does not synthesize auth cookies from JSON token bodies without backend Set-Cookie', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        getSetCookie: () => [],
        get: () => null,
      },
      json: async () => ({
        access_token: 'json_access_token_value',
        refresh_token: 'json_refresh_token_value',
        token_type: 'bearer',
        expires_in: 3600,
      }),
    } as unknown as Response) as typeof fetch;

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'en-EN',
      '/en-EN/dashboard',
      false,
    );
    const request = new NextRequest('http://portal.localhost:3004/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '654321' }),
      headers: {
        'content-type': 'application/json',
        host: 'portal.localhost:3004',
      },
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);
    const setCookieHeaders = readSetCookieHeaders(response).join('\n');

    expect(response.status).toBe(200);
    expect(setCookieHeaders).not.toContain('access_token=json_access_token_value');
    expect(setCookieHeaders).not.toContain('refresh_token=json_refresh_token_value');
  });

  it('rejects requests without a valid pending 2FA cookie', async () => {
    const request = new NextRequest('http://localhost:3002/api/auth/2fa/complete', {
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
