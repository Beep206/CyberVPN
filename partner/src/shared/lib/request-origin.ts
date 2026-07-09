import type { NextRequest } from 'next/server';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

const APPROVED_LOCAL_STAGE_PARTNER_ORIGINS = new Set([
  'http://portal.localhost:3004',
  'http://storefront.localhost:3004',
  'http://127.0.0.1:3004',
  'http://localhost:3004',
  'http://portal.localhost:3002',
  'http://storefront.localhost:3002',
  'http://127.0.0.1:3002',
  'http://localhost:3002',
]);

function normalizeOrigin(value: string | null | undefined): string | null {
  if (!value) return null;

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function originFromHost(rawHost: string | null | undefined, protocol: string): string | null {
  if (!rawHost) return null;

  const host = rawHost
    .split(',')[0]
    ?.trim()
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/\/.*$/, '');

  if (!host || /[\r\n]/.test(host) || host.includes('\\') || host.includes('@')) {
    return null;
  }

  return normalizeOrigin(`${protocol}://${host}`);
}

function getRequestContextOrigins(request: NextRequest): Set<string> {
  const origins = new Set<string>([SITE_URL, request.nextUrl.origin]);
  const requestOrigin = normalizeOrigin(request.url);
  if (requestOrigin) {
    origins.add(requestOrigin);
  }

  const forwardedProto = request.headers.get('x-forwarded-proto')?.split(',')[0]?.trim() || 'http';
  const protocol = forwardedProto === 'https' ? 'https' : 'http';

  for (const headerName of ['host', 'x-forwarded-host']) {
    const origin = originFromHost(request.headers.get(headerName), protocol);
    if (origin) {
      origins.add(origin);
    }
  }

  return origins;
}

function getAllowedOrigins(request: NextRequest): Set<string> {
  const allowedOrigins = getRequestContextOrigins(request);

  if ([...allowedOrigins].some((origin) => APPROVED_LOCAL_STAGE_PARTNER_ORIGINS.has(origin))) {
    for (const origin of APPROVED_LOCAL_STAGE_PARTNER_ORIGINS) {
      allowedOrigins.add(origin);
    }
  }

  return allowedOrigins;
}

export function isAllowedAppOrigin(request: NextRequest): boolean {
  const origin = request.headers.get('origin');
  const referer = request.headers.get('referer');
  const allowedOrigins = getAllowedOrigins(request);

  if (origin && allowedOrigins.has(origin)) {
    return true;
  }

  if (!referer) {
    return false;
  }

  try {
    return allowedOrigins.has(new URL(referer).origin);
  } catch {
    return false;
  }
}
