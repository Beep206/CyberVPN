import type { NextRequest } from 'next/server';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

export function isAllowedAppOrigin(request: NextRequest): boolean {
  const origin = request.headers.get('origin');
  const referer = request.headers.get('referer');
  const allowedOrigins = new Set([SITE_URL, request.nextUrl.origin]);

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
