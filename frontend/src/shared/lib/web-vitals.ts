/**
 * Web Vitals Performance Tracking
 *
 * Tracks Core Web Vitals and custom performance marks.
 * Integrates with Sentry for performance monitoring.
 */

import * as Sentry from '@sentry/nextjs';

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
    // Create browser performance mark
    performance.mark(name);

    // Send to Sentry with metadata
    Sentry.addBreadcrumb({
      category: 'performance',
      message: `Performance mark: ${name}`,
      level: 'info',
      data: metadata,
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
    const measure = endMark
      ? performance.measure(name, startMark, endMark)
      : performance.measure(name, startMark);

    // Send measurement to Sentry
    Sentry.metrics.distribution(name, measure.duration, {
      unit: 'millisecond',
    });

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

    // Core Web Vitals
    onCLS((metric: { value: number; rating: string }) => {
      Sentry.metrics.distribution('web-vitals.cls', metric.value, {
        unit: 'none',
      });
    });

    onLCP((metric: { value: number; rating: string }) => {
      Sentry.metrics.distribution('web-vitals.lcp', metric.value, {
        unit: 'millisecond',
      });
    });

    onINP((metric: { value: number; rating: string }) => {
      Sentry.metrics.distribution('web-vitals.inp', metric.value, {
        unit: 'millisecond',
      });
    });

    // Additional metrics
    onFCP((metric: { value: number; rating: string }) => {
      Sentry.metrics.distribution('web-vitals.fcp', metric.value, {
        unit: 'millisecond',
      });
    });

    onTTFB((metric: { value: number; rating: string }) => {
      Sentry.metrics.distribution('web-vitals.ttfb', metric.value, {
        unit: 'millisecond',
      });
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
