import * as Sentry from '@sentry/nextjs';
import { NextResponse, type NextRequest } from 'next/server';
import {
  PRODUCT_ANALYTICS_EVENT_DEFINITIONS,
  sanitizeProductAnalyticsCapture,
  type ProductAnalyticsEventName,
} from '@/lib/product-intelligence/contracts';
import { capturePartnerProductEvent } from '@/lib/product-intelligence/server';
import { isAllowedAppOrigin } from '@/shared/lib/request-origin';

function buildMetricAttributes(event: ProductAnalyticsEventName, deliveryStatus: string) {
  const definition = PRODUCT_ANALYTICS_EVENT_DEFINITIONS[event];

  return {
    delivery_status: deliveryStatus,
    event,
    owner: definition.owner,
    source_class: definition.sourceClass,
  };
}

export async function POST(request: NextRequest) {
  try {
    if (!isAllowedAppOrigin(request)) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }

    const capture = sanitizeProductAnalyticsCapture(
      (await request.json()) as {
        distinctId?: unknown;
        event?: unknown;
        properties?: Record<string, unknown>;
      },
    );

    if (!capture) {
      return NextResponse.json({ error: 'invalid_payload' }, { status: 400 });
    }

    const result = await capturePartnerProductEvent(capture);

    Sentry.metrics.distribution('product_intelligence.capture', 1, {
      unit: 'none',
      attributes: buildMetricAttributes(capture.event, result.status),
    } as never);

    Sentry.addBreadcrumb({
      category: 'product_intelligence',
      level: result.status === 'rejected' ? 'warning' : 'info',
      message: capture.event,
      data: {
        deliveryStatus: result.status,
        distinctId: capture.distinctId,
        event: capture.event,
      },
    });

    return new NextResponse(null, {
      status: 204,
      headers: {
        'Cache-Control': 'no-store',
        'X-Product-Analytics-Status': result.status,
      },
    });
  } catch {
    return NextResponse.json({ error: 'invalid_payload' }, { status: 400 });
  }
}
