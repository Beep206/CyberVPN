import * as Sentry from '@sentry/nextjs';
import { NextResponse, type NextRequest } from 'next/server';
import {
  getFrontendRuntimeEvents,
  recordFrontendRuntimeEvent,
  type FrontendRuntimePayload,
} from '@/shared/lib/analytics-reporting';
import { isAllowedAppOrigin } from '@/shared/lib/request-origin';

function getBackendBaseUrl(): string | null {
  const baseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  return baseUrl ? baseUrl.replace(/\/$/, '') : null;
}

function getFrontendObservabilitySecret(): string | null {
  const secret = process.env.FRONTEND_OBSERVABILITY_INTERNAL_SECRET?.trim();
  return secret || null;
}

const ALLOWED_EVENTS = new Set<FrontendRuntimePayload['event']>([
  'route_load',
  'api_call',
  'route_guard_block',
  'form_validation_error',
  'submit_attempt',
  'submit_failure',
  'unhandled_error',
  'render_error',
]);
const ALLOWED_ROUTE_GROUPS = new Set(['auth', 'dashboard', 'marketing', 'miniapp']);
const ALLOWED_SURFACES = new Set<FrontendRuntimePayload['surface']>(['partner_portal']);

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

function sanitizePath(value: string | undefined): string {
  if (!value) {
    return '/';
  }

  return value.trim().slice(0, 256) || '/';
}

function sanitizeFrontendRuntimePayload(payload: FrontendRuntimePayload): FrontendRuntimePayload {
  return {
    blockedReason: payload.blockedReason ? sanitizeToken(payload.blockedReason) : undefined,
    connectionType: sanitizeToken(payload.connectionType),
    deviceBucket: sanitizeToken(payload.deviceBucket),
    durationMs: typeof payload.durationMs === 'number' && Number.isFinite(payload.durationMs)
      ? Math.max(payload.durationMs, 0)
      : undefined,
    endpointTemplate: payload.endpointTemplate ? sanitizePath(payload.endpointTemplate) : undefined,
    errorCode: payload.errorCode ? sanitizeToken(payload.errorCode) : undefined,
    event: ALLOWED_EVENTS.has(payload.event) ? payload.event : 'route_load',
    formName: payload.formName ? sanitizeToken(payload.formName) : undefined,
    lane: payload.lane ? sanitizeToken(payload.lane) : undefined,
    locale: payload.locale?.slice(0, 16),
    method: payload.method ? sanitizeToken(payload.method) : undefined,
    path: sanitizePath(payload.path),
    reducedMotion: sanitizeToken(payload.reducedMotion),
    releaseRing: payload.releaseRing ? sanitizeToken(payload.releaseRing) : undefined,
    requestId: payload.requestId?.slice(0, 128),
    result: payload.result ? sanitizeToken(payload.result) : undefined,
    routeGroup: ALLOWED_ROUTE_GROUPS.has(payload.routeGroup) ? payload.routeGroup : 'marketing',
    saveData: sanitizeToken(payload.saveData),
    surface: ALLOWED_SURFACES.has(payload.surface) ? payload.surface : 'partner_portal',
    viewportBucket: sanitizeToken(payload.viewportBucket),
    workspaceStatus: payload.workspaceStatus ? sanitizeToken(payload.workspaceStatus) : undefined,
  };
}

function buildMetricName(event: FrontendRuntimePayload['event']): string {
  return `frontend.${event}`;
}

function buildMetricValue(payload: FrontendRuntimePayload): number {
  return payload.durationMs ?? 1;
}

function buildMetricUnit(payload: FrontendRuntimePayload): 'millisecond' | 'none' {
  return payload.durationMs != null ? 'millisecond' : 'none';
}

function buildMetricAttributes(payload: FrontendRuntimePayload): Record<string, string> {
  return {
    blocked_reason: payload.blockedReason ?? 'none',
    endpoint_template: payload.endpointTemplate ?? 'none',
    error_code: payload.errorCode ?? 'none',
    event: payload.event,
    form_name: payload.formName ?? 'none',
    lane: payload.lane ?? 'none',
    method: payload.method ?? 'none',
    release_ring: payload.releaseRing ?? 'none',
    result: payload.result ?? 'none',
    route_group: payload.routeGroup,
    surface: payload.surface,
    workspace_status: payload.workspaceStatus ?? 'none',
  };
}

async function forwardFrontendRuntimePayload(
  request: NextRequest,
  payload: FrontendRuntimePayload,
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
  if (payload.requestId) {
    headers.set('x-request-id', payload.requestId);
  }

  const response = await fetch(`${baseUrl}/api/v1/monitoring/frontend-runtime-events`, {
    method: 'POST',
    cache: 'no-store',
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`frontend_runtime_forward_failed:${response.status}`);
  }
}

export async function POST(request: NextRequest) {
  try {
    if (!isAllowedAppOrigin(request)) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }

    const payload = sanitizeFrontendRuntimePayload(
      (await request.json()) as FrontendRuntimePayload,
    );

    recordFrontendRuntimeEvent(payload);

    Sentry.metrics.distribution(buildMetricName(payload.event), buildMetricValue(payload), {
      unit: buildMetricUnit(payload),
      attributes: buildMetricAttributes(payload),
    } as never);

    Sentry.addBreadcrumb({
      category: 'frontend.runtime',
      level: payload.event === 'unhandled_error' || payload.event === 'render_error' ? 'error' : 'info',
      message: payload.event,
      data: {
        endpointTemplate: payload.endpointTemplate,
        errorCode: payload.errorCode,
        event: payload.event,
        formName: payload.formName,
        path: payload.path,
        requestId: payload.requestId,
        routeGroup: payload.routeGroup,
        surface: payload.surface,
      },
    });

    try {
      await forwardFrontendRuntimePayload(request, payload);
    } catch (error) {
      Sentry.captureException(error, {
        tags: {
          event: payload.event,
          surface: payload.surface,
          telemetry: 'frontend_runtime_forward',
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

export function GET() {
  return NextResponse.json({
    events: getFrontendRuntimeEvents(),
  });
}
