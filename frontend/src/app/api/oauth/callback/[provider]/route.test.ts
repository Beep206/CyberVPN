import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { NextRequest } from 'next/server';

import { GET } from './route';
import {
  createOAuthTransactionCookieValue,
  OAUTH_TRANSACTION_COOKIE,
} from '@/features/auth/lib/oauth-transaction';
import {
  parsePendingTwoFactorCookieValue,
  PENDING_2FA_COOKIE,
} from '@/features/auth/lib/pending-twofa';
import { OAUTH_PROVIDER_QUERY_PARAM } from '@/features/auth/lib/oauth-error-codes';
import { OAUTH_RESULT_COOKIE } from '@/features/auth/lib/session';

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

describe('GET /api/oauth/callback/[provider]', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('forwards callback to backend, propagates cookies, and redirects new users to welcome flow', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: 'access_token_value',
          refresh_token: 'refresh_token_value',
          token_type: 'bearer',
          expires_in: 3600,
          user: {
            id: 'usr_1',
            login: 'neo',
            email: 'neo@cybervpn.io',
            is_active: true,
            is_email_verified: true,
            created_at: '2026-03-31T00:00:00Z',
          },
          is_new_user: true,
          requires_2fa: false,
          tfa_token: null,
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

    const transaction = createOAuthTransactionCookieValue('google', 'ru-RU', null);
    const request = new NextRequest(
      'http://localhost:3000/api/oauth/callback/google?code=auth_code&state=csrf123',
    );
    request.cookies.set(OAUTH_TRANSACTION_COOKIE, transaction.cookieValue);

    const response = await GET(request, {
      params: Promise.resolve({ provider: 'google' }),
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/oauth/google/login/callback',
      expect.objectContaining({
        body: JSON.stringify({ code: 'auth_code', state: 'csrf123' }),
        cache: 'no-store',
        method: 'POST',
      }),
    );
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('http://localhost:3000/ru-RU/dashboard?welcome=true');
    expect(readSetCookieHeaders(response).join('\n')).toContain('access_token=abc');
    expect(response.cookies.get(OAUTH_RESULT_COOKIE)?.value).toBe('google');
  });

  it('redirects 2FA responses back to localized login page', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: '',
          refresh_token: '',
          token_type: 'bearer',
          expires_in: 0,
          user: {
            id: 'usr_2',
            login: 'morpheus',
            email: 'morpheus@cybervpn.io',
            is_active: true,
            is_email_verified: true,
            created_at: '2026-03-31T00:00:00Z',
          },
          is_new_user: false,
          requires_2fa: true,
          tfa_token: 'pending_2fa_token',
        }),
        {
          status: 200,
          headers: {
            'content-type': 'application/json',
          },
        },
      ),
    ) as typeof fetch;

    const transaction = createOAuthTransactionCookieValue('discord', 'ru-RU', '/ru-RU/dashboard/servers');
    const request = new NextRequest(
      'http://localhost:3000/api/oauth/callback/discord?code=auth_code&state=csrf123',
    );
    request.cookies.set(OAUTH_TRANSACTION_COOKIE, transaction.cookieValue);

    const response = await GET(request, {
      params: Promise.resolve({ provider: 'discord' }),
    });

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe(
      'http://localhost:3000/ru-RU/login?2fa=true&oauth_provider=discord',
    );
    expect(parsePendingTwoFactorCookieValue(response.cookies.get(PENDING_2FA_COOKIE)?.value)).toEqual({
      token: 'pending_2fa_token',
      locale: 'ru-RU',
      returnTo: '/ru-RU/dashboard/servers',
      isNewUser: false,
    });
  });

  it('maps backend state failures to a stable login error code', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ detail: 'Invalid or expired OAuth state.' }),
        {
          status: 401,
          headers: {
            'content-type': 'application/json',
          },
        },
      ),
    ) as typeof fetch;

    const transaction = createOAuthTransactionCookieValue('google', 'ru-RU', '/ru-RU/dashboard');
    const request = new NextRequest(
      'http://localhost:3000/api/oauth/callback/google?code=auth_code&state=csrf123',
    );
    request.cookies.set(OAUTH_TRANSACTION_COOKIE, transaction.cookieValue);

    const response = await GET(request, {
      params: Promise.resolve({ provider: 'google' }),
    });

    expect(response.headers.get('location')).toBe(
      'http://localhost:3000/ru-RU/login?oauth_error=oauth_state_invalid&oauth_provider=google',
    );
  });

  it('maps provider-denied callbacks to provider_denied', async () => {
    const transaction = createOAuthTransactionCookieValue('github', 'ru-RU', '/ru-RU/dashboard');
    const request = new NextRequest(
      'http://localhost:3000/api/oauth/callback/github?error=access_denied',
    );
    request.cookies.set(OAUTH_TRANSACTION_COOKIE, transaction.cookieValue);

    const response = await GET(request, {
      params: Promise.resolve({ provider: 'github' }),
    });

    const location = new URL(response.headers.get('location') ?? 'http://localhost');
    expect(location.searchParams.get('oauth_error')).toBe('provider_denied');
    expect(location.searchParams.get(OAUTH_PROVIDER_QUERY_PARAM)).toBe('github');
  });
});
