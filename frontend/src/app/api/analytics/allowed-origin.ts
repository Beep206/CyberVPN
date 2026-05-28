import type { NextRequest } from 'next/server';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

const STATIC_ALLOWED_ANALYTICS_ORIGINS = new Set([
  SITE_URL,
  'https://cyber-vpn.net',
  'https://www.cyber-vpn.net',
  'https://my.cyber-vpn.net',
  'https://admin.cyber-vpn.net',
  'https://partner.cyber-vpn.net',
  'https://cyber-vpn.org',
  'https://www.cyber-vpn.org',
  'http://127.0.0.1:9001',
  'http://localhost:3000',
]);

function normalizeOrigin(value: string | null): string | null {
  if (!value) return null;

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

export function hasAllowedAnalyticsOrigin(request: NextRequest): boolean {
  const allowedOrigins = new Set(STATIC_ALLOWED_ANALYTICS_ORIGINS);
  allowedOrigins.add(request.nextUrl.origin);

  const origin = normalizeOrigin(request.headers.get('origin'));
  if (origin && allowedOrigins.has(origin)) {
    return true;
  }

  const refererOrigin = normalizeOrigin(request.headers.get('referer'));
  return Boolean(refererOrigin && allowedOrigins.has(refererOrigin));
}
