import { describe, expect, it } from 'vitest';
import type { NextRequest } from 'next/server';

import { isAllowedAppOrigin } from '@/shared/lib/request-origin';

function createRequest({
  origin,
  referer,
  nextOrigin = 'http://127.0.0.1:3001',
}: {
  origin?: string;
  referer?: string;
  nextOrigin?: string;
}): NextRequest {
  return {
    headers: new Headers({
      ...(origin ? { origin } : {}),
      ...(referer ? { referer } : {}),
    }),
    nextUrl: {
      origin: nextOrigin,
    },
  } as NextRequest;
}

describe('isAllowedAppOrigin', () => {
  it('accepts the admin.localhost dev origin used by authenticated local smoke tests', () => {
    expect(
      isAllowedAppOrigin(
        createRequest({
          origin: 'http://admin.localhost:3001',
          referer: 'http://admin.localhost:3001/ru-RU/dashboard',
        }),
      ),
    ).toBe(true);
  });

  it('accepts admin.localhost through Referer when browsers omit Origin', () => {
    expect(
      isAllowedAppOrigin(
        createRequest({
          referer: 'http://admin.localhost:3001/ru-RU/security/passkeys',
        }),
      ),
    ).toBe(true);
  });

  it('rejects a foreign Origin even when Referer points at an allowed admin route', () => {
    expect(
      isAllowedAppOrigin(
        createRequest({
          origin: 'https://evil.example',
          referer: 'http://admin.localhost:3001/ru-RU/dashboard',
        }),
      ),
    ).toBe(false);
  });
});
