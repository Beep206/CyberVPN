import { NextResponse, type NextRequest } from 'next/server';
import { recordWebVitalEvent, type WebVitalPayload } from '@/shared/lib/analytics-reporting';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

const ALLOWED_METRICS = new Set<WebVitalPayload['metric']>(['cls', 'fcp', 'inp', 'lcp', 'ttfb']);
const ALLOWED_ROUTE_GROUPS = new Set(['auth', 'dashboard', 'marketing', 'miniapp']);

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

function sanitizeWebVitalPayload(payload: WebVitalPayload): WebVitalPayload {
  return {
    connectionType: payload.connectionType.slice(0, 32) || 'unknown',
    deviceBucket: payload.deviceBucket.slice(0, 32) || 'unknown',
    locale: payload.locale?.slice(0, 16),
    metric: ALLOWED_METRICS.has(payload.metric) ? payload.metric : 'lcp',
    path: payload.path.slice(0, 256) || '/',
    rating: payload.rating.slice(0, 32) || 'unknown',
    reducedMotion: payload.reducedMotion.slice(0, 32) || 'unknown',
    routeGroup: ALLOWED_ROUTE_GROUPS.has(payload.routeGroup) ? payload.routeGroup : 'marketing',
    saveData: payload.saveData.slice(0, 32) || 'unknown',
    value: Number.isFinite(payload.value) ? payload.value : 0,
    viewportBucket: payload.viewportBucket.slice(0, 32) || 'unknown',
  };
}

export async function POST(request: NextRequest) {
  try {
    if (!hasAllowedOrigin(request)) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }

    const payload = sanitizeWebVitalPayload((await request.json()) as WebVitalPayload);
    recordWebVitalEvent(payload);

    return new NextResponse(null, {
      status: 204,
      headers: {
        'Cache-Control': 'no-store',
      },
    });
  } catch {
    return NextResponse.json({ error: 'invalid_payload' }, { status: 400 });
  }
}
