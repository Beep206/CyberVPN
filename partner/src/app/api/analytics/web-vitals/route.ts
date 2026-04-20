import { NextResponse, type NextRequest } from 'next/server';
import { recordWebVitalEvent, type WebVitalPayload } from '@/shared/lib/analytics-reporting';
import { isAllowedAppOrigin } from '@/shared/lib/request-origin';

const ALLOWED_METRICS = new Set<WebVitalPayload['metric']>(['cls', 'fcp', 'inp', 'lcp', 'ttfb']);
const ALLOWED_ROUTE_GROUPS = new Set(['auth', 'dashboard', 'marketing', 'miniapp']);

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
    if (!isAllowedAppOrigin(request)) {
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
