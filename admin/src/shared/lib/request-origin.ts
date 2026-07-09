import type { NextRequest } from 'next/server';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

const APPROVED_LOCAL_ADMIN_ORIGINS = new Set([
  'http://localhost:3001',
  'http://127.0.0.1:3001',
  'http://admin.localhost:3001',
  'http://localhost:13001',
  'http://127.0.0.1:13001',
  'http://admin.localhost:13001',
]);

function normalizeOrigin(value: string | null): string | null {
  if (!value) return null;

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function allowedOriginsForRequest(request: NextRequest): Set<string> {
  const allowedOrigins = new Set<string>();
  const siteOrigin = normalizeOrigin(SITE_URL);
  const requestOrigin = normalizeOrigin(request.nextUrl.origin);

  if (siteOrigin) {
    allowedOrigins.add(siteOrigin);
  }

  if (requestOrigin) {
    allowedOrigins.add(requestOrigin);
  }

  if (process.env.NODE_ENV !== 'production') {
    for (const origin of APPROVED_LOCAL_ADMIN_ORIGINS) {
      allowedOrigins.add(origin);
    }
  }

  return allowedOrigins;
}

export function isAllowedAppOrigin(request: NextRequest): boolean {
  const origin = normalizeOrigin(request.headers.get('origin'));
  const referer = request.headers.get('referer');
  const allowedOrigins = allowedOriginsForRequest(request);

  if (origin) {
    return allowedOrigins.has(origin);
  }

  if (!referer) {
    return false;
  }

  const refererOrigin = normalizeOrigin(referer);
  return refererOrigin ? allowedOrigins.has(refererOrigin) : false;
}
