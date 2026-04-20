import type { NextRequest } from 'next/server';

function readForwardedValue(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const firstValue = value.split(',')[0]?.trim();
  return firstValue || null;
}

export function getRequestOrigin(request: NextRequest): string {
  const forwardedProtocol = readForwardedValue(request.headers.get('x-forwarded-proto'));
  const forwardedHost = readForwardedValue(request.headers.get('x-forwarded-host'));
  const host = forwardedHost ?? readForwardedValue(request.headers.get('host'));

  if (!host) {
    return request.nextUrl.origin;
  }

  const protocol = forwardedProtocol ?? request.nextUrl.protocol.replace(/:$/, '');
  return `${protocol}://${host}`;
}

export function buildAppUrl(request: NextRequest, pathname: string): URL {
  return new URL(pathname, getRequestOrigin(request));
}
