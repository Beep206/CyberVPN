import { beforeEach, describe, expect, it } from 'vitest';
import { GET } from './route';
import {
  recordAcquisitionEvent,
  recordWebVitalEvent,
  resetAnalyticsReportingStore,
} from '@/shared/lib/analytics-reporting';

function createRequest(origin = 'https://vpn.ozoxy.ru', nextOrigin = 'https://vpn.ozoxy.ru') {
  return {
    headers: new Headers({
      referer: `${origin}/en-EN/analytics`,
    }),
    nextUrl: {
      origin: nextOrigin,
    },
  };
}

describe('GET /api/analytics/reporting', () => {
  beforeEach(() => {
    resetAnalyticsReportingStore();
  });

  it('returns aggregated acquisition and web vital summaries', async () => {
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
    recordWebVitalEvent({
      connectionType: '4g',
      deviceBucket: 'desktop',
      locale: 'en-EN',
      metric: 'lcp',
      path: '/en-EN/pricing',
      rating: 'good',
      reducedMotion: 'no-preference',
      routeGroup: 'marketing',
      saveData: 'off',
      value: 1900,
      viewportBucket: 'desktop',
    });

    const response = await GET(createRequest() as never);
    const summary = await response.json();

    expect(response.status).toBe(200);
    expect(summary.acquisition.ctaClicks).toBe(1);
    expect(summary.ctas[0]).toEqual({
      ctaId: 'download',
      clicks: 1,
    });
    expect(summary.webVitals.metrics).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          metric: 'lcp',
          p75: 1900,
        }),
      ]),
    );
  });

  it('rejects foreign origins', async () => {
    const response = await GET(
      createRequest('https://evil.example', 'https://vpn.ozoxy.ru') as never,
    );

    expect(response.status).toBe(403);
  });
});
