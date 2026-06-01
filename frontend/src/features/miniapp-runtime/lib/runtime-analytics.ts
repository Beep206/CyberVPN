'use client';

export type MiniAppRuntimeEventName =
  | 'miniapp_opened'
  | 'miniapp_bootstrap_loaded'
  | 'miniapp_bootstrap_failed'
  | 'miniapp_checkout_started'
  | 'miniapp_checkout_completed'
  | 'miniapp_checkout_failed'
  | 'miniapp_payment_status_resolved'
  | 'miniapp_config_loaded'
  | 'miniapp_config_failed';

type MiniAppRuntimePayload = {
  event: MiniAppRuntimeEventName;
  page: 'home' | 'plans' | 'profile' | 'vpn';
  locale: string;
  path: string;
  errorCode?: string;
  checkoutFlow?: string;
  configSource?: string;
  paymentRail?: string;
  paymentStatus?: string;
  primaryCtaKind?: string;
  subscriptionStatus?: string;
};

function getConnectionType(): string {
  const connection = (navigator as Navigator & {
    connection?: { effectiveType?: string };
  }).connection;
  return connection?.effectiveType ?? 'unknown';
}

function getSaveData(): string {
  const connection = (navigator as Navigator & {
    connection?: { saveData?: boolean };
  }).connection;
  return connection?.saveData ? 'on' : 'off';
}

function getReducedMotion(): string {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'reduce' : 'no-preference';
}

function getViewportBucket(): string {
  const width = window.innerWidth;
  if (width < 640) return 'mobile-compact';
  if (width < 1024) return 'mobile-regular';
  return 'desktop';
}

function getDeviceBucket(): string {
  const touchCapable =
    typeof navigator.maxTouchPoints === 'number'
    ? navigator.maxTouchPoints > 0
    : 'ontouchstart' in window;
  return touchCapable ? 'mobile-touch' : 'desktop';
}

export async function emitMiniAppRuntimeEvent(payload: MiniAppRuntimePayload): Promise<void> {
  const body = JSON.stringify({
    ...payload,
    connectionType: getConnectionType(),
    deviceBucket: getDeviceBucket(),
    reducedMotion: getReducedMotion(),
    routeGroup: 'miniapp',
    saveData: getSaveData(),
    viewportBucket: getViewportBucket(),
  });

  if (typeof navigator.sendBeacon === 'function') {
    navigator.sendBeacon('/api/analytics/miniapp-runtime', body);
    return;
  }

  await fetch('/api/analytics/miniapp-runtime', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
    keepalive: true,
  });
}
