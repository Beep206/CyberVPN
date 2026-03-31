import type { AnalyticsProvider, EventProperties } from '@/lib/analytics';

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

function hasGtag(): boolean {
  return typeof window !== 'undefined' && typeof window.gtag === 'function';
}

function normalizeEventName(event: string): string {
  const normalized = event
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, '_')
    .replace(/^_+|_+$/g, '');

  return normalized.slice(0, 40) || 'event';
}

function normalizeParameterKey(key: string): string {
  const normalized = key
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, '_')
    .replace(/^_+|_+$/g, '');

  return normalized.slice(0, 40);
}

function normalizeParameterValue(value: EventProperties[string]): number | string | undefined {
  if (typeof value === 'number' || typeof value === 'string') {
    return value;
  }

  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }

  return undefined;
}

function normalizeEventParameters(
  properties?: EventProperties,
): Record<string, number | string> | undefined {
  if (!properties) {
    return undefined;
  }

  const entries = Object.entries(properties).flatMap(([key, value]) => {
    const normalizedKey = normalizeParameterKey(key);
    const normalizedValue = normalizeParameterValue(value);

    if (!normalizedKey || normalizedValue === undefined) {
      return [];
    }

    return [[normalizedKey, normalizedValue] as const];
  });

  if (entries.length === 0) {
    return undefined;
  }

  return Object.fromEntries(entries);
}

export function createGa4Provider(measurementId: string): AnalyticsProvider {
  return {
    track(event, properties) {
      if (!hasGtag()) {
        return;
      }

      window.gtag?.('event', normalizeEventName(event), normalizeEventParameters(properties) ?? {});
    },

    identify(userId, traits) {
      if (!hasGtag()) {
        return;
      }

      window.gtag?.('config', measurementId, { user_id: userId });

      const normalizedTraits = normalizeEventParameters(traits);

      if (normalizedTraits) {
        window.gtag?.('set', 'user_properties', normalizedTraits);
      }
    },

    reset() {
      if (!hasGtag()) {
        return;
      }

      window.gtag?.('config', measurementId, { user_id: null });
    },
  };
}
