import * as Sentry from '@sentry/nextjs';
import { NextResponse, type NextRequest } from 'next/server';
import { recordWebVitalEvent, type WebVitalPayload } from '@/shared/lib/analytics-reporting';
import { isAllowedAppOrigin } from '@/shared/lib/request-origin';

const ALLOWED_METRICS = new Set<WebVitalPayload['metric']>(['cls', 'fcp', 'inp', 'lcp', 'ttfb']);
const ALLOWED_ROUTE_GROUPS = new Set(['auth', 'dashboard', 'marketing', 'miniapp']);
const FRONTEND_SURFACE = 'partner_portal';

function getBackendBaseUrl(): string | null {
  const baseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  return baseUrl ? baseUrl.replace(/\/$/, '') : null;
}

function getFrontendObservabilitySecret(): string | null {
  const secret = process.env.FRONTEND_OBSERVABILITY_INTERNAL_SECRET?.trim();
  return secret || null;
}

function sanitizeToken(value: string | undefined, fallback = 'unknown'): string {
  if (!value) {
    return fallback;
  }

  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._/-]+/g, '_')
    .slice(0, 80);

  return normalized || fallback;
}

function sanitizeWebVitalPayload(payload: WebVitalPayload): WebVitalPayload {
  return {
    connectionType: sanitizeToken(payload.connectionType),
    deviceBucket: sanitizeToken(payload.deviceBucket),
    locale: payload.locale?.slice(0, 16),
    metric: ALLOWED_METRICS.has(payload.metric) ? payload.metric : 'lcp',
    path: payload.path.slice(0, 256) || '/',
    rating: sanitizeToken(payload.rating),
    reducedMotion: sanitizeToken(payload.reducedMotion),
    routeGroup: ALLOWED_ROUTE_GROUPS.has(payload.routeGroup) ? payload.routeGroup : 'marketing',
    saveData: sanitizeToken(payload.saveData),
    value: Number.isFinite(payload.value) ? payload.value : 0,
    viewportBucket: sanitizeToken(payload.viewportBucket),
  };
}

async function forwardWebVitalPayload(
  request: NextRequest,
  payload: WebVitalPayload,
): Promise<void> {
  const baseUrl = getBackendBaseUrl();
  const secret = getFrontendObservabilitySecret();

  if (!baseUrl || !secret) {
    return;
  }

  const headers = new Headers({
    accept: 'application/json',
    'content-type': 'application/json',
    'x-frontend-observability-secret': secret,
  });

  const forwardedFor = request.headers.get('x-forwarded-for');
  const userAgent = request.headers.get('user-agent');
  const acceptLanguage = request.headers.get('accept-language');

  if (forwardedFor) {
    headers.set('x-forwarded-for', forwardedFor);
  }
  if (userAgent) {
    headers.set('user-agent', userAgent);
  }
  if (acceptLanguage) {
    headers.set('accept-language', acceptLanguage);
  }

  const response = await fetch(`${baseUrl}/api/v1/monitoring/frontend-web-vitals`, {
    method: 'POST',
    cache: 'no-store',
    headers,
    body: JSON.stringify({
      ...payload,
      surface: FRONTEND_SURFACE,
    }),
  });

  if (!response.ok) {
    throw new Error(`frontend_web_vitals_forward_failed:${response.status}`);
  }
}

export async function POST(request: NextRequest) {
  try {
    if (!isAllowedAppOrigin(request)) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }

    const payload = sanitizeWebVitalPayload((await request.json()) as WebVitalPayload);
    recordWebVitalEvent(payload);

    Sentry.addBreadcrumb({
      category: 'web-vitals',
      level: 'info',
      message: payload.metric,
      data: {
        path: payload.path,
        rating: payload.rating,
        routeGroup: payload.routeGroup,
        surface: FRONTEND_SURFACE,
        value: payload.value,
      },
    });

    try {
      await forwardWebVitalPayload(request, payload);
    } catch (error) {
      Sentry.captureException(error, {
        tags: {
          metric: payload.metric,
          surface: FRONTEND_SURFACE,
          telemetry: 'frontend_web_vitals_forward',
        },
      });
    }

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
