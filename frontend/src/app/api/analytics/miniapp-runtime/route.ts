import * as Sentry from '@sentry/nextjs';
import { NextResponse, type NextRequest } from 'next/server';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

type MiniAppRuntimeRoutePayload = {
  event:
    | 'miniapp_opened'
    | 'miniapp_bootstrap_loaded'
    | 'miniapp_bootstrap_failed'
    | 'miniapp_checkout_started'
    | 'miniapp_checkout_completed'
    | 'miniapp_checkout_failed'
    | 'miniapp_payment_status_resolved'
    | 'miniapp_config_loaded'
    | 'miniapp_config_failed';
  page: 'home' | 'plans' | 'profile';
  locale?: string;
  path: string;
  connectionType: string;
  deviceBucket: string;
  reducedMotion: string;
  routeGroup: 'miniapp';
  saveData: string;
  viewportBucket: string;
  checkoutFlow?: string;
  configSource?: string;
  errorCode?: string;
  paymentRail?: string;
  paymentStatus?: string;
  primaryCtaKind?: string;
  subscriptionStatus?: string;
};

const ALLOWED_EVENTS = new Set<MiniAppRuntimeRoutePayload['event']>([
  'miniapp_opened',
  'miniapp_bootstrap_loaded',
  'miniapp_bootstrap_failed',
  'miniapp_checkout_started',
  'miniapp_checkout_completed',
  'miniapp_checkout_failed',
  'miniapp_payment_status_resolved',
  'miniapp_config_loaded',
  'miniapp_config_failed',
]);

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

function sanitizeToken(value: string | undefined, fallback = 'none', maxLength = 64): string {
  const normalized = (value ?? '').trim().slice(0, maxLength);
  return normalized || fallback;
}

export async function POST(request: NextRequest) {
  try {
    if (!hasAllowedOrigin(request)) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }

    const payload = (await request.json()) as MiniAppRuntimeRoutePayload;
    if (!ALLOWED_EVENTS.has(payload.event)) {
      return NextResponse.json({ error: 'invalid_event' }, { status: 400 });
    }

    const sanitized = {
      event: payload.event,
      page: payload.page === 'plans' ? 'plans' : payload.page === 'profile' ? 'profile' : 'home',
      locale: sanitizeToken(payload.locale, 'unknown', 16),
      path: sanitizeToken(payload.path, '/', 256),
      checkoutFlow: sanitizeToken(payload.checkoutFlow, 'none', 32),
      connectionType: sanitizeToken(payload.connectionType, 'unknown', 32),
      configSource: sanitizeToken(payload.configSource, 'none', 64),
      deviceBucket: sanitizeToken(payload.deviceBucket, 'unknown', 32),
      reducedMotion: sanitizeToken(payload.reducedMotion, 'unknown', 32),
      routeGroup: 'miniapp',
      saveData: sanitizeToken(payload.saveData, 'unknown', 32),
      viewportBucket: sanitizeToken(payload.viewportBucket, 'unknown', 32),
      errorCode: sanitizeToken(payload.errorCode, 'none', 64),
      paymentRail: sanitizeToken(payload.paymentRail, 'none', 32),
      paymentStatus: sanitizeToken(payload.paymentStatus, 'none', 32),
      primaryCtaKind: sanitizeToken(payload.primaryCtaKind, 'none', 32),
      subscriptionStatus: sanitizeToken(payload.subscriptionStatus, 'none', 32),
    } as const;

    Sentry.metrics.distribution('miniapp.runtime_event', 1, {
      unit: 'none',
      attributes: {
        checkout_flow: sanitized.checkoutFlow,
        connection_type: sanitized.connectionType,
        config_source: sanitized.configSource,
        device_bucket: sanitized.deviceBucket,
        error_code: sanitized.errorCode,
        event: sanitized.event,
        locale: sanitized.locale,
        page: sanitized.page,
        path: sanitized.path,
        payment_rail: sanitized.paymentRail,
        payment_status: sanitized.paymentStatus,
        primary_cta_kind: sanitized.primaryCtaKind,
        reduced_motion: sanitized.reducedMotion,
        route_group: sanitized.routeGroup,
        save_data: sanitized.saveData,
        subscription_status: sanitized.subscriptionStatus,
        viewport_bucket: sanitized.viewportBucket,
      },
    } as never);

    Sentry.addBreadcrumb({
      category: 'miniapp',
      level: sanitized.event === 'miniapp_bootstrap_failed' || sanitized.event === 'miniapp_config_failed' || sanitized.event === 'miniapp_checkout_failed'
        ? 'warning'
        : 'info',
      message: sanitized.event,
      data: {
        checkoutFlow: sanitized.checkoutFlow,
        configSource: sanitized.configSource,
        errorCode: sanitized.errorCode,
        page: sanitized.page,
        path: sanitized.path,
        paymentRail: sanitized.paymentRail,
        paymentStatus: sanitized.paymentStatus,
        primaryCtaKind: sanitized.primaryCtaKind,
        subscriptionStatus: sanitized.subscriptionStatus,
      },
    });

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
