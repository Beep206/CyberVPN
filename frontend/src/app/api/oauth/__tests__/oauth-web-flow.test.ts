import { beforeEach, describe, expect, it, vi, afterEach } from 'vitest';
import { NextRequest } from 'next/server';

import { GET as startHandler } from '../start/[provider]/route';
import { GET as callbackHandler } from '../callback/[provider]/route';
import { OAUTH_TRANSACTION_COOKIE } from '@/features/auth/lib/oauth-transaction';
import { OAUTH_RESULT_COOKIE } from '@/features/auth/lib/session';

function readSetCookieHeaders(response: Response): string[] {
  const headers = response.headers as Headers & {
    getSetCookie?: () => string[];
  };

  if (typeof headers.getSetCookie === 'function') {
    return headers.getSetCookie();
  }

  const headerValue = response.headers.get('set-cookie');
  return headerValue ? [headerValue] : [];
}

describe('OAuth web flow route integration', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('completes start and callback flow with transaction cookie and forwarded auth cookies', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            authorize_url: 'https://github.com/login/oauth/authorize?state=csrf123',
          }),
          {
            status: 200,
            headers: { 'content-type': 'application/json' },
          },
        ),
      )
      .mockResolvedValueOnce(
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
            is_new_user: false,
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

    const startRequest = new NextRequest(
      'http://localhost:3000/api/oauth/start/github?locale=ru-RU&return_to=%2Fru-RU%2Fdashboard%2Fservers',
    );
    const startResponse = await startHandler(startRequest, {
      params: Promise.resolve({ provider: 'github' }),
    });

    expect(startResponse.status).toBe(307);
    expect(startResponse.headers.get('location')).toBe(
      'https://github.com/login/oauth/authorize?state=csrf123',
    );

    const txCookie = startResponse.cookies.get(OAUTH_TRANSACTION_COOKIE)?.value;
    expect(txCookie).toBeTruthy();

    const callbackRequest = new NextRequest(
      'http://localhost:3000/api/oauth/callback/github?code=auth_code&state=csrf123',
    );
    callbackRequest.cookies.set(OAUTH_TRANSACTION_COOKIE, txCookie ?? '');

    const callbackResponse = await callbackHandler(callbackRequest, {
      params: Promise.resolve({ provider: 'github' }),
    });

    expect(callbackResponse.status).toBe(307);
    expect(callbackResponse.headers.get('location')).toBe(
      'http://localhost:3000/ru-RU/dashboard/servers',
    );
    expect(readSetCookieHeaders(callbackResponse).join('\n')).toContain('access_token=abc');
    expect(callbackResponse.cookies.get(OAUTH_RESULT_COOKIE)?.value).toBe('github');
  });

  it('maps backend collisions to a stable login error redirect', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            authorize_url: 'https://accounts.google.com/o/oauth2/v2/auth?state=csrf456',
          }),
          {
            status: 200,
            headers: { 'content-type': 'application/json' },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            detail: 'Automatic account linking is disabled for this provider email. Sign in with your existing account and link the provider manually.',
          }),
          {
            status: 409,
            headers: { 'content-type': 'application/json' },
          },
        ),
      ) as typeof fetch;

    const startRequest = new NextRequest(
      'http://localhost:3000/api/oauth/start/google?locale=ru-RU&return_to=%2Fru-RU%2Fdashboard',
    );
    const startResponse = await startHandler(startRequest, {
      params: Promise.resolve({ provider: 'google' }),
    });

    const callbackRequest = new NextRequest(
      'http://localhost:3000/api/oauth/callback/google?code=auth_code&state=csrf456',
    );
    callbackRequest.cookies.set(
      OAUTH_TRANSACTION_COOKIE,
      startResponse.cookies.get(OAUTH_TRANSACTION_COOKIE)?.value ?? '',
    );

    const callbackResponse = await callbackHandler(callbackRequest, {
      params: Promise.resolve({ provider: 'google' }),
    });

    expect(callbackResponse.headers.get('location')).toBe(
      'http://localhost:3000/ru-RU/login?oauth_error=oauth_linking_required&oauth_provider=google',
    );
  });
});
