'use client';

import { useQuery } from '@tanstack/react-query';
import { Bot, Gauge, MousePointerClick, Route, Sparkles } from 'lucide-react';

type SeoDashboardSummary = {
  acquisition: {
    aiReferralSessions: number;
    aiToCtaRate: number;
    ctaClicks: number;
    lastUpdatedAt?: string;
    pageViews: number;
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
      metric: 'cls' | 'inp' | 'lcp';
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

const METRIC_LABELS: Record<'cls' | 'inp' | 'lcp', string> = {
  cls: 'CLS p75',
  inp: 'INP p75',
  lcp: 'LCP p75',
};

function formatMetricValue(metric: 'cls' | 'inp' | 'lcp', value: number): string {
  if (metric === 'cls') {
    return value.toFixed(3);
  }

  return `${Math.round(value)}ms`;
}

function formatSourceName(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatCtaLabel(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

async function fetchSeoDashboardSummary(): Promise<SeoDashboardSummary> {
  const response = await fetch('/api/analytics/reporting', {
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`Failed to load SEO dashboard: ${response.status}`);
  }

  return response.json();
}

export function AcquisitionAnalyticsPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['analytics', 'seo-dashboard'],
    queryFn: fetchSeoDashboardSummary,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <div className="cyber-card p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 w-64 rounded-xs bg-neon-cyan/10" />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            {Array.from({ length: 4 }, (_, index) => (
              <div key={index} className="h-24 rounded border border-grid-line/30 bg-terminal-bg/60" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="cyber-card p-6">
        <div className="flex items-center gap-3 text-neon-pink">
          <Sparkles className="h-5 w-5" />
          <div>
            <h3 className="font-display text-lg">SEO / AI Acquisition Loop</h3>
            <p className="font-mono text-sm text-muted-foreground">
              Reporting is unavailable right now. Acquisition ingestion remains active.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const vitalMetrics = data.webVitals.metrics.filter((metric) => metric.samples > 0);

  return (
    <section className="space-y-6">
      <div className="cyber-card p-6">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-neon-cyan" />
              <h3 className="text-xl font-display text-neon-cyan">SEO / AI Acquisition Loop</h3>
            </div>
            <p className="font-mono text-sm text-muted-foreground">
              Live same-process snapshot for acquisition routes and recent marketing page vitals.
            </p>
          </div>
          <p className="font-mono text-xs text-muted-foreground">
            {data.acquisition.lastUpdatedAt
              ? `Updated ${new Date(data.acquisition.lastUpdatedAt).toLocaleString()}`
              : 'Waiting for new telemetry'}
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded border border-neon-cyan/20 bg-neon-cyan/5 p-4">
            <div className="mb-3 flex items-center gap-2 text-neon-cyan">
              <Bot className="h-4 w-4" />
              <span className="font-mono text-xs uppercase tracking-[0.2em]">AI Sessions</span>
            </div>
            <p className="text-3xl font-display text-neon-cyan">{data.acquisition.aiReferralSessions}</p>
          </div>

          <div className="rounded border border-matrix-green/20 bg-matrix-green/5 p-4">
            <div className="mb-3 flex items-center gap-2 text-matrix-green">
              <Route className="h-4 w-4" />
              <span className="font-mono text-xs uppercase tracking-[0.2em]">Page Views</span>
            </div>
            <p className="text-3xl font-display text-matrix-green">{data.acquisition.pageViews}</p>
          </div>

          <div className="rounded border border-neon-purple/20 bg-neon-purple/5 p-4">
            <div className="mb-3 flex items-center gap-2 text-neon-purple">
              <MousePointerClick className="h-4 w-4" />
              <span className="font-mono text-xs uppercase tracking-[0.2em]">CTA Clicks</span>
            </div>
            <p className="text-3xl font-display text-neon-purple">{data.acquisition.ctaClicks}</p>
          </div>

          <div className="rounded border border-warning/20 bg-warning/5 p-4">
            <div className="mb-3 flex items-center gap-2 text-warning">
              <Gauge className="h-4 w-4" />
              <span className="font-mono text-xs uppercase tracking-[0.2em]">AI to CTA</span>
            </div>
            <p className="text-3xl font-display text-warning">{data.acquisition.aiToCtaRate}%</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="cyber-card p-6">
          <h4 className="mb-4 font-display text-lg text-neon-cyan">Source Breakdown</h4>
          <div className="space-y-3">
            {data.sources.length > 0 ? (
              data.sources.map((source) => (
                <div
                  key={source.sourceName}
                  className="flex items-center justify-between rounded border border-grid-line/30 bg-terminal-bg/50 px-4 py-3"
                >
                  <div>
                    <p className="font-mono text-sm text-foreground">{formatSourceName(source.sourceName)}</p>
                    <p className="font-mono text-xs text-muted-foreground">{source.sessions} sessions</p>
                  </div>
                  <p className="font-display text-lg text-neon-cyan">{source.ctaClicks}</p>
                </div>
              ))
            ) : (
              <p className="font-mono text-sm text-muted-foreground">No acquisition source data yet.</p>
            )}
          </div>
        </div>

        <div className="cyber-card p-6">
          <h4 className="mb-4 font-display text-lg text-neon-purple">Route Yield</h4>
          <div className="space-y-3">
            {data.routes.length > 0 ? (
              data.routes.map((route) => (
                <div
                  key={route.path}
                  className="rounded border border-grid-line/30 bg-terminal-bg/50 px-4 py-3"
                >
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <p className="break-all font-mono text-sm text-foreground">{route.path}</p>
                    <span className="font-display text-neon-purple">{route.ctaClicks}</span>
                  </div>
                  <div className="flex gap-4 font-mono text-xs text-muted-foreground">
                    <span>{route.pageViews} views</span>
                    <span>{route.aiSessions} AI</span>
                    <span>{route.ctaClicks} CTA</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="font-mono text-sm text-muted-foreground">No route-level acquisition data yet.</p>
            )}
          </div>
        </div>

        <div className="cyber-card p-6">
          <h4 className="mb-4 font-display text-lg text-warning">Conversion Intents</h4>
          <div className="space-y-3">
            {data.ctas.length > 0 ? (
              data.ctas.map((cta) => (
                <div
                  key={cta.ctaId}
                  className="flex items-center justify-between rounded border border-grid-line/30 bg-terminal-bg/50 px-4 py-3"
                >
                  <p className="font-mono text-sm text-foreground">{formatCtaLabel(cta.ctaId)}</p>
                  <span className="font-display text-warning">{cta.clicks}</span>
                </div>
              ))
            ) : (
              <p className="font-mono text-sm text-muted-foreground">No CTA telemetry yet.</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="cyber-card p-6">
          <h4 className="mb-4 font-display text-lg text-matrix-green">Marketing Web Vitals</h4>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {vitalMetrics.length > 0 ? (
              vitalMetrics.map((metric) => (
                <div
                  key={metric.metric}
                  className="rounded border border-grid-line/30 bg-terminal-bg/50 px-4 py-4"
                >
                  <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    {METRIC_LABELS[metric.metric]}
                  </p>
                  <p className="mt-3 font-display text-2xl text-matrix-green">
                    {formatMetricValue(metric.metric, metric.p75)}
                  </p>
                  <p className="mt-2 font-mono text-xs text-muted-foreground">
                    {metric.goodRate}% good over {metric.samples} samples
                  </p>
                </div>
              ))
            ) : (
              <p className="font-mono text-sm text-muted-foreground md:col-span-3">
                No marketing page vitals collected yet.
              </p>
            )}
          </div>
        </div>

        <div className="cyber-card p-6">
          <h4 className="mb-4 font-display text-lg text-matrix-green">Route Health</h4>
          <div className="space-y-3">
            {data.webVitals.routes.length > 0 ? (
              data.webVitals.routes.map((route) => (
                <div
                  key={route.path}
                  className="rounded border border-grid-line/30 bg-terminal-bg/50 px-4 py-3"
                >
                  <p className="mb-2 break-all font-mono text-sm text-foreground">{route.path}</p>
                  <div className="flex flex-wrap gap-4 font-mono text-xs text-muted-foreground">
                    <span>LCP {route.lcp ? `${route.lcp}ms` : 'n/a'}</span>
                    <span>INP {route.inp ? `${route.inp}ms` : 'n/a'}</span>
                    <span>CLS {route.cls ? route.cls.toFixed(3) : 'n/a'}</span>
                    <span>{route.samples} samples</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="font-mono text-sm text-muted-foreground">No route health data yet.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
