import * as Sentry from '@sentry/nextjs';
import { NextResponse, type NextRequest } from 'next/server';
import { recordAcquisitionEvent } from '@/shared/lib/analytics-reporting';
import {
  sanitizeAcquisitionPayload,
  type AcquisitionPayload,
} from '@/shared/lib/ai-seo-analytics';
import { isAllowedAppOrigin } from '@/shared/lib/request-origin';

const ALLOWED_EVENTS = new Set<AcquisitionPayload['event']>(['page_view', 'cta_click']);
const ALLOWED_ROUTE_GROUPS = new Set(['auth', 'marketing']);

function buildMetricName(event: AcquisitionPayload['event']): string {
  return event === 'cta_click' ? 'acquisition.cta_click' : 'acquisition.page_view';
}

function buildMetricAttributes(payload: AcquisitionPayload): Record<string, string> {
  return {
    connection_type: payload.connectionType,
    cta_id: payload.ctaId ?? 'none',
    cta_zone: payload.ctaZone ?? 'none',
    device_bucket: payload.deviceBucket,
    locale: payload.locale ?? 'unknown',
    path: payload.path,
    page_title: payload.pageTitle ?? 'unknown',
    reduced_motion: payload.reducedMotion,
    referrer_host: payload.referrerHost ?? 'direct',
    route_group: payload.routeGroup,
    save_data: payload.saveData,
    source_name: payload.sourceName,
    source_type: payload.sourceType,
    utm_campaign: payload.utmCampaign ?? 'none',
    utm_content: payload.utmContent ?? 'none',
    utm_medium: payload.utmMedium ?? 'none',
    utm_source: payload.utmSource ?? 'none',
    utm_term: payload.utmTerm ?? 'none',
    viewport_bucket: payload.viewportBucket,
  };
}

export async function POST(request: NextRequest) {
  try {
    if (!isAllowedAppOrigin(request)) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }

    const payload = sanitizeAcquisitionPayload((await request.json()) as AcquisitionPayload);

    if (!ALLOWED_EVENTS.has(payload.event)) {
      return NextResponse.json({ error: 'invalid_event' }, { status: 400 });
    }

    if (!ALLOWED_ROUTE_GROUPS.has(payload.routeGroup)) {
      return NextResponse.json({ error: 'invalid_route_group' }, { status: 400 });
    }

    recordAcquisitionEvent(payload);

    Sentry.metrics.distribution(buildMetricName(payload.event), 1, {
      unit: 'none',
      attributes: buildMetricAttributes(payload),
    } as never);

    Sentry.addBreadcrumb({
      category: 'acquisition',
      level: 'info',
      message: payload.event,
      data: {
        ctaId: payload.ctaId,
        ctaZone: payload.ctaZone,
        locale: payload.locale,
        path: payload.path,
        pageTitle: payload.pageTitle,
        sourceName: payload.sourceName,
        sourceType: payload.sourceType,
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
