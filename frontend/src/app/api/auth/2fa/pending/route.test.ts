import { describe, expect, it } from 'vitest';
import { NextRequest } from 'next/server';

import { GET, POST } from './route';
import {
  createPendingTwoFactorCookieValue,
  parsePendingTwoFactorCookieValue,
  PENDING_2FA_COOKIE,
} from '@/features/auth/lib/pending-twofa';

describe('POST /api/auth/2fa/pending', () => {
  it('stores a signed pending-2fa cookie', async () => {
    const request = new NextRequest('http://localhost:3000/api/auth/2fa/pending', {
      method: 'POST',
      body: JSON.stringify({
        token: 'pending_2fa_token',
        locale: 'ru-RU',
        return_to: '/ru-RU/dashboard/servers',
        is_new_user: true,
      }),
      headers: {
        'content-type': 'application/json',
      },
    });

    const response = await POST(request);
    const cookie = response.cookies.get(PENDING_2FA_COOKIE);

    expect(response.status).toBe(204);
    expect(cookie).toBeDefined();
    expect(parsePendingTwoFactorCookieValue(cookie?.value)).toEqual({
      token: 'pending_2fa_token',
      locale: 'ru-RU',
      returnTo: '/ru-RU/dashboard/servers',
      isNewUser: true,
    });
  });

  it('rejects requests without a pending token', async () => {
    const request = new NextRequest('http://localhost:3000/api/auth/2fa/pending', {
      method: 'POST',
      body: JSON.stringify({ locale: 'ru-RU' }),
      headers: {
        'content-type': 'application/json',
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toEqual({
      detail: 'Missing pending 2FA token.',
    });
  });
});

describe('GET /api/auth/2fa/pending', () => {
  it('returns public pending metadata for a valid pending-2fa cookie', async () => {
    const pending = createPendingTwoFactorCookieValue(
      'pending_2fa_token',
      'ru-RU',
      '/ru-RU/dashboard',
      true,
    );
    const request = new NextRequest('http://localhost:3000/api/auth/2fa/pending', {
      method: 'GET',
    });
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await GET(request);

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      pending: true,
      locale: 'ru-RU',
      return_to: '/ru-RU/dashboard',
      is_new_user: true,
    });
  });

  it('clears stale or malformed pending-2fa cookies', async () => {
    const request = new NextRequest('http://localhost:3000/api/auth/2fa/pending', {
      method: 'GET',
    });
    request.cookies.set(PENDING_2FA_COOKIE, 'not-a-valid-cookie');

    const response = await GET(request);

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ pending: false });
    expect(response.cookies.get(PENDING_2FA_COOKIE)?.value).toBe('');
  });
});
