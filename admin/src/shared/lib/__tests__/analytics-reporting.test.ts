import { describe, expect, it, beforeEach } from 'vitest';
import {
  getSeoDashboardSummary,
  recordAcquisitionEvent,
  recordWebVitalEvent,
  resetAnalyticsReportingStore,
} from '@/shared/lib/analytics-reporting';

describe('analytics-reporting', () => {
  beforeEach(() => {
    resetAnalyticsReportingStore();
  });

  it('aggregates acquisition events by source, route, and CTA', () => {
    recordAcquisitionEvent({
      connectionType: '4g',
      deviceBucket: 'desktop',
      event: 'page_view',
      locale: 'en-EN',
      path: '/en-EN/pricing',
      reducedMotion: 'no-preference',
      routeGroup: 'marketing',
      saveData: 'off',
      sourceName: 'chatgpt',
      sourceType: 'ai',
      viewportBucket: 'desktop',
    });
    recordAcquisitionEvent({
      connectionType: '4g',
      ctaHref: '/download',
      ctaId: 'download',
      ctaZone: 'landing_hero',
      deviceBucket: 'desktop',
      event: 'cta_click',
      locale: 'en-EN',
      path: '/en-EN/pricing',
      reducedMotion: 'no-preference',
      routeGroup: 'marketing',
      saveData: 'off',
      sourceName: 'chatgpt',
      sourceType: 'ai',
      viewportBucket: 'desktop',
    });

    const summary = getSeoDashboardSummary();

    expect(summary.acquisition.aiReferralSessions).toBe(1);
    expect(summary.acquisition.ctaClicks).toBe(1);
    expect(summary.ctas[0]).toEqual({
      ctaId: 'download',
      clicks: 1,
    });
    expect(summary.routes[0]).toMatchObject({
      aiSessions: 1,
      ctaClicks: 1,
      pageViews: 1,
      path: '/en-EN/pricing',
    });
    expect(summary.sources[0]).toMatchObject({
      ctaClicks: 1,
      sessions: 1,
      sourceName: 'chatgpt',
    });
  });

  it('aggregates marketing web vitals into route-level p75 summaries', () => {
    recordWebVitalEvent({
      connectionType: '4g',
      deviceBucket: 'mobile-touch',
      locale: 'en-EN',
      metric: 'lcp',
      path: '/en-EN/pricing',
      rating: 'good',
      reducedMotion: 'no-preference',
      routeGroup: 'marketing',
      saveData: 'off',
      value: 1800,
      viewportBucket: 'mobile-regular',
    });
    recordWebVitalEvent({
      connectionType: '4g',
      deviceBucket: 'mobile-touch',
      locale: 'en-EN',
      metric: 'inp',
      path: '/en-EN/pricing',
      rating: 'good',
      reducedMotion: 'no-preference',
      routeGroup: 'marketing',
      saveData: 'off',
      value: 120,
      viewportBucket: 'mobile-regular',
    });
    recordWebVitalEvent({
      connectionType: '4g',
      deviceBucket: 'mobile-touch',
      locale: 'en-EN',
      metric: 'cls',
      path: '/en-EN/pricing',
      rating: 'good',
      reducedMotion: 'no-preference',
      routeGroup: 'marketing',
      saveData: 'off',
      value: 0.03,
      viewportBucket: 'mobile-regular',
    });

    const summary = getSeoDashboardSummary();

    expect(summary.webVitals.metrics).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          metric: 'lcp',
          p75: 1800,
          samples: 1,
        }),
        expect.objectContaining({
          metric: 'inp',
          p75: 120,
          samples: 1,
        }),
        expect.objectContaining({
          metric: 'cls',
          p75: 0.03,
          samples: 1,
        }),
      ]),
    );
    expect(summary.webVitals.routes[0]).toMatchObject({
      path: '/en-EN/pricing',
      lcp: 1800,
      inp: 120,
      cls: 0.03,
    });
  });
});
