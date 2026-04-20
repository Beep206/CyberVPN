import type { AcquisitionCtaId, AcquisitionPayload, AcquisitionSourceName } from '@/shared/lib/ai-seo-analytics';

const MAX_ACQUISITION_EVENTS = 500;
const MAX_WEB_VITAL_EVENTS = 500;

type StoredAcquisitionEvent = AcquisitionPayload & {
  timestamp: number;
};

export type WebVitalName = 'cls' | 'fcp' | 'inp' | 'lcp' | 'ttfb';

export type WebVitalPayload = {
  connectionType: string;
  deviceBucket: string;
  locale?: string;
  metric: WebVitalName;
  path: string;
  rating: string;
  reducedMotion: string;
  routeGroup: string;
  saveData: string;
  value: number;
  viewportBucket: string;
};

type StoredWebVitalEvent = WebVitalPayload & {
  timestamp: number;
};

export type SeoDashboardSummary = {
  acquisition: {
    aiReferralSessions: number;
    aiToCtaRate: number;
    lastUpdatedAt?: string;
    pageViews: number;
    ctaClicks: number;
  };
  ctas: Array<{
    ctaId: string;
    clicks: number;
  }>;
  routes: Array<{
    aiSessions: number;
    ctaClicks: number;
    pageViews: number;
    path: string;
  }>;
  sources: Array<{
    ctaClicks: number;
    sessions: number;
    sourceName: string;
  }>;
  webVitals: {
    metrics: Array<{
      goodRate: number;
      metric: WebVitalName;
      p75: number;
      samples: number;
    }>;
    routes: Array<{
      cls?: number;
      inp?: number;
      lcp?: number;
      path: string;
      samples: number;
    }>;
  };
};

type AnalyticsReportingStore = {
  acquisitionEvents: StoredAcquisitionEvent[];
  webVitalEvents: StoredWebVitalEvent[];
};

const STORE_KEY = '__ozoxyAnalyticsReportingStore';

function getStore(): AnalyticsReportingStore {
  const globalStore = globalThis as typeof globalThis & {
    [STORE_KEY]?: AnalyticsReportingStore;
  };

  if (!globalStore[STORE_KEY]) {
    globalStore[STORE_KEY] = {
      acquisitionEvents: [],
      webVitalEvents: [],
    };
  }

  return globalStore[STORE_KEY];
}

function trimStore<T>(items: T[], maxItems: number): T[] {
  if (items.length <= maxItems) {
    return items;
  }

  return items.slice(items.length - maxItems);
}

function round(value: number, digits = 2): number {
  const power = 10 ** digits;
  return Math.round(value * power) / power;
}

function computeP75(values: number[]): number {
  if (values.length === 0) {
    return 0;
  }

  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.floor(sorted.length * 0.75));
  return sorted[index];
}

function toRate(numerator: number, denominator: number): number {
  if (denominator === 0) {
    return 0;
  }

  return round((numerator / denominator) * 100, 1);
}

function normalizePath(path: string): string {
  return path || '/';
}

function getRecentAcquisitionEvents(): StoredAcquisitionEvent[] {
  return getStore().acquisitionEvents.filter(
    (event) => event.routeGroup === 'marketing' || event.routeGroup === 'auth',
  );
}

function getRecentWebVitalEvents(): StoredWebVitalEvent[] {
  return getStore().webVitalEvents.filter((event) => event.routeGroup === 'marketing');
}

function summarizeSources(events: StoredAcquisitionEvent[]) {
  const map = new Map<AcquisitionSourceName, { sessions: number; ctaClicks: number }>();

  for (const event of events) {
    const current = map.get(event.sourceName) ?? { sessions: 0, ctaClicks: 0 };

    if (event.event === 'page_view') {
      current.sessions += 1;
    }

    if (event.event === 'cta_click') {
      current.ctaClicks += 1;
    }

    map.set(event.sourceName, current);
  }

  return [...map.entries()]
    .map(([sourceName, summary]) => ({
      sourceName,
      ...summary,
    }))
    .sort((left, right) => right.sessions - left.sessions || right.ctaClicks - left.ctaClicks)
    .slice(0, 6);
}

function summarizeRoutes(events: StoredAcquisitionEvent[]) {
  const map = new Map<string, { pageViews: number; aiSessions: number; ctaClicks: number }>();

  for (const event of events) {
    const path = normalizePath(event.path);
    const current = map.get(path) ?? { pageViews: 0, aiSessions: 0, ctaClicks: 0 };

    if (event.event === 'page_view') {
      current.pageViews += 1;

      if (event.sourceType === 'ai') {
        current.aiSessions += 1;
      }
    }

    if (event.event === 'cta_click') {
      current.ctaClicks += 1;
    }

    map.set(path, current);
  }

  return [...map.entries()]
    .map(([path, summary]) => ({
      path,
      ...summary,
    }))
    .sort(
      (left, right) =>
        right.pageViews - left.pageViews ||
        right.aiSessions - left.aiSessions ||
        right.ctaClicks - left.ctaClicks,
    )
    .slice(0, 6);
}

function summarizeCtas(events: StoredAcquisitionEvent[]) {
  const map = new Map<AcquisitionCtaId | 'unknown', number>();

  for (const event of events) {
    if (event.event !== 'cta_click') {
      continue;
    }

    const ctaId = event.ctaId ?? 'unknown';
    map.set(ctaId, (map.get(ctaId) ?? 0) + 1);
  }

  return [...map.entries()]
    .map(([ctaId, clicks]) => ({
      ctaId,
      clicks,
    }))
    .sort((left, right) => right.clicks - left.clicks)
    .slice(0, 6);
}

function summarizeWebVitals(events: StoredWebVitalEvent[]) {
  const metricNames: WebVitalName[] = ['lcp', 'inp', 'cls'];

  const metrics = metricNames.map((metric) => {
    const metricEvents = events.filter((event) => event.metric === metric);
    const values = metricEvents.map((event) => event.value);
    const goodSamples = metricEvents.filter((event) => event.rating === 'good').length;

    return {
      metric,
      p75: round(computeP75(values), metric === 'cls' ? 3 : 0),
      samples: metricEvents.length,
      goodRate: toRate(goodSamples, metricEvents.length),
    };
  });

  const routeMap = new Map<
    string,
    {
      cls: number[];
      inp: number[];
      lcp: number[];
      samples: number;
    }
  >();

  for (const event of events) {
    if (event.metric !== 'cls' && event.metric !== 'inp' && event.metric !== 'lcp') {
      continue;
    }

    const path = normalizePath(event.path);
    const current = routeMap.get(path) ?? {
      cls: [],
      inp: [],
      lcp: [],
      samples: 0,
    };

    current[event.metric].push(event.value);
    current.samples += 1;
    routeMap.set(path, current);
  }

  const routes = [...routeMap.entries()]
    .map(([path, summary]) => ({
      path,
      samples: summary.samples,
      cls: summary.cls.length > 0 ? round(computeP75(summary.cls), 3) : undefined,
      inp: summary.inp.length > 0 ? round(computeP75(summary.inp), 0) : undefined,
      lcp: summary.lcp.length > 0 ? round(computeP75(summary.lcp), 0) : undefined,
    }))
    .sort((left, right) => right.samples - left.samples)
    .slice(0, 6);

  return { metrics, routes };
}

export function recordAcquisitionEvent(payload: AcquisitionPayload): void {
  const store = getStore();

  store.acquisitionEvents = trimStore(
    [
      ...store.acquisitionEvents,
      {
        ...payload,
        timestamp: Date.now(),
      },
    ],
    MAX_ACQUISITION_EVENTS,
  );
}

export function recordWebVitalEvent(payload: WebVitalPayload): void {
  const store = getStore();

  store.webVitalEvents = trimStore(
    [
      ...store.webVitalEvents,
      {
        ...payload,
        path: normalizePath(payload.path),
        timestamp: Date.now(),
      },
    ],
    MAX_WEB_VITAL_EVENTS,
  );
}

export function getSeoDashboardSummary(): SeoDashboardSummary {
  const acquisitionEvents = getRecentAcquisitionEvents();
  const webVitalEvents = getRecentWebVitalEvents();
  const pageViews = acquisitionEvents.filter((event) => event.event === 'page_view');
  const ctaClicks = acquisitionEvents.filter((event) => event.event === 'cta_click');
  const aiReferralSessions = pageViews.filter((event) => event.sourceType === 'ai');
  const lastUpdatedAt = [...acquisitionEvents, ...webVitalEvents]
    .sort((left, right) => right.timestamp - left.timestamp)[0]?.timestamp;

  return {
    acquisition: {
      aiReferralSessions: aiReferralSessions.length,
      aiToCtaRate: toRate(ctaClicks.length, aiReferralSessions.length),
      ctaClicks: ctaClicks.length,
      lastUpdatedAt: lastUpdatedAt ? new Date(lastUpdatedAt).toISOString() : undefined,
      pageViews: pageViews.length,
    },
    ctas: summarizeCtas(acquisitionEvents),
    routes: summarizeRoutes(acquisitionEvents),
    sources: summarizeSources(acquisitionEvents),
    webVitals: summarizeWebVitals(webVitalEvents),
  };
}

export function resetAnalyticsReportingStore(): void {
  const store = getStore();
  store.acquisitionEvents = [];
  store.webVitalEvents = [];
}
