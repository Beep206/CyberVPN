/**
 * Web Vitals Performance Tracking
 *
 * Tracks Core Web Vitals and custom performance marks.
 * Integrates with Sentry for performance monitoring.
 */

import * as Sentry from '@sentry/nextjs';
import { getLocaleFromPathname } from '@/shared/lib/ai-seo-analytics';
import { getMobileTelemetryContext } from '@/shared/lib/mobile-device-bucket';

interface WebVitalMetric {
  rating: string;
  value: number;
}

const WEB_VITALS_ENDPOINT = '/api/analytics/web-vitals';

function getPerformanceContextTags(pathname?: string): Record<string, string> {
  const context = getMobileTelemetryContext(pathname);

  return {
    connection_type: context.connectionType,
    device_bucket: context.deviceBucket,
    reduced_motion: context.reducedMotion,
    route_group: context.routeGroup,
    save_data: context.saveData,
    viewport_bucket: context.viewportBucket,
  };
}

function recordDistribution(
  metricName: string,
  value: number,
  unit: 'millisecond' | 'none',
  attributes: Record<string, string>
): void {
  Sentry.metrics.distribution(metricName, value, {
    unit,
    attributes,
  } as never);
}

function sendWebVitalMetric(metric: {
  path: string;
  rating: string;
  metric: 'cls' | 'fcp' | 'inp' | 'lcp' | 'ttfb';
  value: number;
}): void {
  if (typeof window === 'undefined') {
    return;
  }

  const pathname = metric.path || window.location.pathname;
  const context = getMobileTelemetryContext(pathname);
  const body = JSON.stringify({
    connectionType: context.connectionType,
    deviceBucket: context.deviceBucket,
    locale: getLocaleFromPathname(pathname),
    metric: metric.metric,
    path: pathname,
    rating: metric.rating,
    reducedMotion: context.reducedMotion,
    routeGroup: context.routeGroup,
    saveData: context.saveData,
    value: metric.value,
    viewportBucket: context.viewportBucket,
  });

  if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    navigator.sendBeacon(WEB_VITALS_ENDPOINT, new Blob([body], { type: 'application/json' }));
    return;
  }

  void fetch(WEB_VITALS_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
    credentials: 'same-origin',
    keepalive: true,
  });
}

/**
 * Custom performance marks for key user interactions
 */
export const PerformanceMarks = {
  // Page lifecycle
  PAGE_INTERACTIVE: 'page-interactive',
  PAGE_FULLY_LOADED: 'page-fully-loaded',

  // User actions
  PURCHASE_FLOW_START: 'purchase-flow-start',
  PURCHASE_FLOW_COMPLETE: 'purchase-flow-complete',
  WITHDRAWAL_FLOW_START: 'withdrawal-flow-start',
  WITHDRAWAL_FLOW_COMPLETE: 'withdrawal-flow-complete',
  VPN_CONNECTION_START: 'vpn-connection-start',
  VPN_CONNECTION_COMPLETE: 'vpn-connection-complete',

  // Data loading
  DASHBOARD_DATA_LOADED: 'dashboard-data-loaded',
  SERVERS_LIST_LOADED: 'servers-list-loaded',
  ANALYTICS_DATA_LOADED: 'analytics-data-loaded',

  // 3D rendering
  THREE_SCENE_READY: '3d-scene-ready',
  THREE_FIRST_FRAME: '3d-first-frame',
} as const;

/**
 * Mark a custom performance event
 *
 * @param name - Performance mark name
 * @param metadata - Optional metadata to attach to the mark
 */
export function markPerformance(
  name: string,
  metadata?: Record<string, unknown>
): void {
  if (typeof window === 'undefined') return;

  try {
    const context = getPerformanceContextTags();

    // Create browser performance mark
    performance.mark(name);

    // Send to Sentry with metadata
    Sentry.addBreadcrumb({
      category: 'performance',
      message: `Performance mark: ${name}`,
      level: 'info',
      data: {
        ...context,
        ...metadata,
      },
    });
  } catch (error) {
    // Performance API not available or mark failed
    console.error('Failed to create performance mark:', name, error);
  }
}

/**
 * Measure duration between two performance marks
 *
 * @param name - Measure name
 * @param startMark - Start mark name
 * @param endMark - End mark name (defaults to current time)
 * @returns Duration in milliseconds, or null if marks not found
 */
export function measurePerformance(
  name: string,
  startMark: string,
  endMark?: string
): number | null {
  if (typeof window === 'undefined') return null;

  try {
    const context = getPerformanceContextTags();
    const measure = endMark
      ? performance.measure(name, startMark, endMark)
      : performance.measure(name, startMark);

    // Send measurement to Sentry
    recordDistribution(name, measure.duration, 'millisecond', context);

    return measure.duration;
  } catch (error) {
    console.error('Failed to measure performance:', name, error);
    return null;
  }
}

/**
 * Track Web Vitals using native web-vitals library
 * Should be called in root layout client component
 */
export async function reportWebVitals(): Promise<void> {
  if (typeof window === 'undefined') return;

  try {
    const { onCLS, onLCP, onFCP, onTTFB, onINP } = await import('web-vitals');
    const publishMetric = (
      metricName: 'web-vitals.cls' | 'web-vitals.fcp' | 'web-vitals.inp' | 'web-vitals.lcp' | 'web-vitals.ttfb',
      value: number,
      unit: string,
      rating: string
    ) => {
      const path = window.location.pathname;
      const context = getPerformanceContextTags(path);
      const shortMetric = metricName.replace('web-vitals.', '') as 'cls' | 'fcp' | 'inp' | 'lcp' | 'ttfb';
      const attributes = {
        ...context,
        metric: shortMetric,
        rating,
      };

      recordDistribution(
        metricName,
        value,
        unit === 'none' ? 'none' : 'millisecond',
        attributes
      );

      Sentry.addBreadcrumb({
        category: 'web-vitals',
        level: 'info',
        message: metricName,
        data: attributes,
      });

      sendWebVitalMetric({
        metric: shortMetric,
        path,
        rating,
        value,
      });
    };

    // Core Web Vitals
    onCLS((metric: WebVitalMetric) => {
      publishMetric('web-vitals.cls', metric.value, 'none', metric.rating);
    });

    onLCP((metric: WebVitalMetric) => {
      publishMetric(
        'web-vitals.lcp',
        metric.value,
        'millisecond',
        metric.rating
      );
    });

    onINP((metric: WebVitalMetric) => {
      publishMetric(
        'web-vitals.inp',
        metric.value,
        'millisecond',
        metric.rating
      );
    });

    // Additional metrics
    onFCP((metric: WebVitalMetric) => {
      publishMetric(
        'web-vitals.fcp',
        metric.value,
        'millisecond',
        metric.rating
      );
    });

    onTTFB((metric: WebVitalMetric) => {
      publishMetric(
        'web-vitals.ttfb',
        metric.value,
        'millisecond',
        metric.rating
      );
    });
  } catch (error) {
    console.error('Failed to load web-vitals:', error);
  }
}

/**
 * Hook for tracking component mount performance
 *
 * @param componentName - Name of the component
 * @returns Cleanup function
 */
export function usePerformanceTracking(componentName: string): () => void {
  if (typeof window === 'undefined') return () => {};

  const startMark = `${componentName}-mount-start`;
  const endMark = `${componentName}-mount-end`;

  markPerformance(startMark);

  return () => {
    markPerformance(endMark);
    measurePerformance(`${componentName}-mount-duration`, startMark, endMark);
  };
}
