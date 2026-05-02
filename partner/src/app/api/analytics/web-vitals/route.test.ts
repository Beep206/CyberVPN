import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
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

  it('forwards accepted web vital payloads to backend ingest when configured', async () => {
    vi.stubEnv('API_URL', 'http://backend.local');
    vi.stubEnv('FRONTEND_OBSERVABILITY_INTERNAL_SECRET', 'frontend-obs-secret');
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 202 }));
    vi.stubGlobal('fetch', fetchMock);

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
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      'http://backend.local/api/v1/monitoring/frontend-web-vitals',
    );
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = init.headers as Headers;
    expect(headers.get('x-frontend-observability-secret')).toBe('frontend-obs-secret');
    expect(JSON.parse(init.body as string)).toMatchObject({
      metric: 'lcp',
      surface: 'partner_portal',
    });
  });

  it('keeps returning 204 when backend forwarding fails', async () => {
    vi.stubEnv('API_URL', 'http://backend.local');
    vi.stubEnv('FRONTEND_OBSERVABILITY_INTERNAL_SECRET', 'frontend-obs-secret');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('backend down')));

    const response = await POST(
      createRequest({
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
      }) as never,
    );

    expect(response.status).toBe(204);
    expect(getSeoDashboardSummary().webVitals.metrics).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          metric: 'inp',
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
