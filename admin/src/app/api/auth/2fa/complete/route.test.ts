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
  });

  it('completes pending 2FA, forwards backend cookies, and returns redirect target', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: 'access_token_value',
          refresh_token: 'refresh_token_value',
          token_type: 'bearer',
          expires_in: 3600,
        }),
        {
          status: 200,
          headers: {
            'content-type': 'application/json',
            'set-cookie': 'access_token=abc; Path=/; HttpOnly',
          },
        },
      ),
    ) as typeof fetch;

    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'ru-RU',
      '/ru-RU/dashboard',
      true,
    );
    const request = new NextRequest('https://admin.cyber-vpn.net/api/auth/2fa/complete', {
      method: 'POST',
      body: JSON.stringify({ code: '123456' }),
      headers: {
        'content-type': 'application/json',
        'x-forwarded-for': '203.0.113.10',
        'x-forwarded-proto': 'https',
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
    const forwardedHeaders = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[1]?.headers as Headers;
    expect(forwardedHeaders.get('x-forwarded-host')).toBe('admin.cyber-vpn.net');
    expect(forwardedHeaders.get('x-forwarded-proto')).toBe('https');
    expect(forwardedHeaders.get('x-forwarded-for')).toBe('203.0.113.10');
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      redirect_to: '/ru-RU/dashboard?welcome=true',
    });
    expect(readSetCookieHeaders(response).join('\n')).toContain('access_token=');
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
