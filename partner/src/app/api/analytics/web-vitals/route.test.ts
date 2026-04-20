import { beforeEach, describe, expect, it } from 'vitest';
import { POST } from './route';
import { getSeoDashboardSummary, resetAnalyticsReportingStore } from '@/shared/lib/analytics-reporting';

function createRequest(
  body: unknown,
  origin = 'https://vpn.ozoxy.ru',
  nextOrigin = 'https://vpn.ozoxy.ru',
) {
  return {
    headers: new Headers({
      referer: `${origin}/en-EN/pricing`,
    }),
    json: async () => body,
    nextUrl: {
      origin: nextOrigin,
    },
  };
}

describe('POST /api/analytics/web-vitals', () => {
  beforeEach(() => {
    resetAnalyticsReportingStore();
  });

  it('accepts valid web vital payloads and stores them for reporting', async () => {
    const response = await POST(
      createRequest({
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
      }) as never,
    );

    expect(response.status).toBe(204);
    expect(getSeoDashboardSummary().webVitals.metrics).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          metric: 'lcp',
          p75: 1800,
          samples: 1,
        }),
      ]),
    );
  });

  it('rejects foreign origins', async () => {
    const response = await POST(
      createRequest(
        {
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
        },
        'https://evil.example',
      ) as never,
    );

    expect(response.status).toBe(403);
  });
});
