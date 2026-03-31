import { describe, expect, it } from 'vitest';
import { NextRequest } from 'next/server';

import { POST } from './route';
import {
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
