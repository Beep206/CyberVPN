import { beforeEach, describe, expect, it } from 'vitest';
import { POST } from './route';
import { getSeoDashboardSummary, resetAnalyticsReportingStore } from '@/shared/lib/analytics-reporting';

function createRequest(
  body: unknown,
  origin = 'https://cyber-vpn.net',
  nextOrigin = 'https://cyber-vpn.net',
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

  it('accepts the customer cabinet origin when the route is served behind another origin', async () => {
    const response = await POST(
      createRequest(
        {
          connectionType: '4g',
          deviceBucket: 'desktop',
          locale: 'ru-RU',
          metric: 'inp',
          path: '/ru-RU/login',
          rating: 'good',
          reducedMotion: 'no-preference',
          routeGroup: 'auth',
          saveData: 'off',
          value: 120,
          viewportBucket: 'desktop',
        },
        'https://my.cyber-vpn.net',
        'https://cyber-vpn.net',
      ) as never,
    );

    expect(response.status).toBe(204);
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
