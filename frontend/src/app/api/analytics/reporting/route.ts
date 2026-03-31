import { NextResponse, type NextRequest } from 'next/server';
import { getSeoDashboardSummary } from '@/shared/lib/analytics-reporting';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

function hasAllowedOrigin(request: NextRequest): boolean {
  const origin = request.headers.get('origin');
  const referer = request.headers.get('referer');
  const allowedOrigins = new Set([
    SITE_URL,
    request.nextUrl.origin,
    'http://127.0.0.1:9001',
    'http://localhost:3000',
  ]);

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

export async function GET(request: NextRequest) {
  if (!hasAllowedOrigin(request)) {
    return NextResponse.json({ error: 'forbidden' }, { status: 403 });
  }

  return NextResponse.json(getSeoDashboardSummary(), {
    headers: {
      'Cache-Control': 'no-store',
    },
  });
}
