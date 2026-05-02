import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GET, POST } from './route';
import {
  getFrontendRuntimeEvents,
  resetAnalyticsReportingStore,
} from '@/shared/lib/analytics-reporting';

function createRequest(
  body: unknown,
  origin = 'https://admin.ozoxy.ru',
  nextOrigin = 'https://admin.ozoxy.ru',
) {
  return {
    headers: new Headers({
      referer: `${origin}/ru-RU/dashboard`,
    }),
    json: async () => body,
    nextUrl: {
      origin: nextOrigin,
    },
  };
}

describe('POST /api/analytics/frontend-runtime', () => {
  beforeEach(() => {
    resetAnalyticsReportingStore();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it('accepts admin frontend runtime payloads and stores them', async () => {
    const response = await POST(
      createRequest({
        connectionType: '4g',
        deviceBucket: 'desktop',
        durationMs: 420,
        endpointTemplate: '/api/v1/auth/session',
        event: 'api_call',
        locale: 'ru-RU',
        method: 'get',
        path: '/ru-RU/dashboard',
        reducedMotion: 'no-preference',
        requestId: 'req-1',
        result: 'success',
        routeGroup: 'dashboard',
        saveData: 'off',
        surface: 'admin_portal',
        viewportBucket: 'desktop',
      }) as never,
    );

    expect(response.status).toBe(204);
    expect(getFrontendRuntimeEvents()).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          event: 'api_call',
          path: '/ru-RU/dashboard',
          requestId: 'req-1',
          routeGroup: 'dashboard',
          surface: 'admin_portal',
        }),
      ]),
    );
  });

  it('forwards accepted payloads to backend ingest when configured', async () => {
    vi.stubEnv('API_URL', 'http://backend.local');
    vi.stubEnv('FRONTEND_OBSERVABILITY_INTERNAL_SECRET', 'frontend-obs-secret');
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 202 }));
    vi.stubGlobal('fetch', fetchMock);

    const response = await POST(
      createRequest({
        connectionType: '4g',
        deviceBucket: 'desktop',
        durationMs: 420,
        endpointTemplate: '/api/v1/auth/session',
        event: 'api_call',
        locale: 'ru-RU',
        method: 'get',
        path: '/ru-RU/dashboard',
        reducedMotion: 'no-preference',
        requestId: 'req-1',
        result: 'success',
        routeGroup: 'dashboard',
        saveData: 'off',
        surface: 'admin_portal',
        viewportBucket: 'desktop',
      }) as never,
    );

    expect(response.status).toBe(204);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      'http://backend.local/api/v1/monitoring/frontend-runtime-events',
    );
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = init.headers as Headers;
    expect(headers.get('x-frontend-observability-secret')).toBe('frontend-obs-secret');
    expect(headers.get('x-request-id')).toBe('req-1');
  });

  it('rejects foreign origins', async () => {
    const response = await POST(
      createRequest(
        {
          connectionType: '4g',
          deviceBucket: 'desktop',
          event: 'route_load',
          path: '/ru-RU/dashboard',
          reducedMotion: 'no-preference',
          routeGroup: 'dashboard',
          saveData: 'off',
          surface: 'admin_portal',
          viewportBucket: 'desktop',
        },
        'https://evil.example',
      ) as never,
    );

    expect(response.status).toBe(403);
  });

  it('returns the stored runtime events via GET', async () => {
    await POST(
      createRequest({
        connectionType: '4g',
        deviceBucket: 'desktop',
        event: 'route_load',
        path: '/ru-RU/dashboard',
        reducedMotion: 'no-preference',
        routeGroup: 'dashboard',
        saveData: 'off',
        surface: 'admin_portal',
        viewportBucket: 'desktop',
      }) as never,
    );

    const response = GET();
    const body = await response.json();

    expect(body.events).toHaveLength(1);
    expect(body.events[0]).toMatchObject({
      event: 'route_load',
      path: '/ru-RU/dashboard',
    });
  });
});
