'use client';

import { sanitizeProductAnalyticsCapture, type ProductAnalyticsCaptureInput } from './contracts';

const PRODUCT_ANALYTICS_ENDPOINT = '/api/analytics/product-events';

export function sendProductAnalyticsEvent(input: ProductAnalyticsCaptureInput | null): void {
  const capture = sanitizeProductAnalyticsCapture(input);
  if (!capture) {
    return;
  }

  const body = JSON.stringify(capture);

  if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    navigator.sendBeacon(PRODUCT_ANALYTICS_ENDPOINT, new Blob([body], { type: 'application/json' }));
    return;
  }

  void fetch(PRODUCT_ANALYTICS_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
    credentials: 'same-origin',
    keepalive: true,
  });
}
