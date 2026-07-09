import { describe, expect, it } from 'vitest';
import type { NextRequest } from 'next/server';
import { isAllowedAppOrigin } from '@/shared/lib/request-origin';

function createRequest({
  host,
  origin,
  referer,
  nextOrigin = 'http://127.0.0.1:3002',
  url = `${nextOrigin}/api/analytics/web-vitals`,
}: {
  host?: string;
  origin?: string;
  referer?: string;
  nextOrigin?: string;
  url?: string;
}): NextRequest {
  const headers = new Headers();
  if (host) headers.set('host', host);
  if (origin) headers.set('origin', origin);
  if (referer) headers.set('referer', referer);

  return {
    headers,
    url,
    nextUrl: {
      origin: nextOrigin,
    },
  } as NextRequest;
}

describe('partner request origin checks', () => {
  it('accepts approved local portal origins when the app is served from a local stage host', () => {
    const request = createRequest({
      origin: 'http://portal.localhost:3002',
    });

    expect(isAllowedAppOrigin(request)).toBe(true);
  });

  it('accepts approved local storefront referers when the app is served from a local stage host', () => {
    const request = createRequest({
      referer: 'http://storefront.localhost:3002/ru-RU/checkout',
    });

    expect(isAllowedAppOrigin(request)).toBe(true);
  });

  it('accepts approved local storefront origins when the request host is storefront-local', () => {
    const request = createRequest({
      host: 'storefront.localhost:3002',
      origin: 'http://storefront.localhost:3002',
      nextOrigin: 'http://portal.localhost:3002',
      url: 'http://storefront.localhost:3002/api/analytics/web-vitals',
    });

    expect(isAllowedAppOrigin(request)).toBe(true);
  });

  it('does not allow local stage origins for production partner requests', () => {
    const request = createRequest({
      origin: 'http://portal.localhost:3002',
      nextOrigin: 'https://partner.cyber-vpn.net',
      url: 'https://partner.cyber-vpn.net/api/analytics/web-vitals',
    });

    expect(isAllowedAppOrigin(request)).toBe(false);
  });

  it('rejects foreign origins', () => {
    const request = createRequest({
      origin: 'https://evil.example',
    });

    expect(isAllowedAppOrigin(request)).toBe(false);
  });
});
