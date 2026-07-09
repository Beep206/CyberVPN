import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { POST } from './route';

const { addBreadcrumb, metricsDistribution } = vi.hoisted(() => ({
  addBreadcrumb: vi.fn(),
  metricsDistribution: vi.fn(),
}));

vi.mock('@sentry/nextjs', () => ({
  addBreadcrumb,
  metrics: {
    distribution: metricsDistribution,
  },
}));

function createRequest(
  body: unknown,
  origin = 'https://cyber-vpn.net',
  nextOrigin = 'https://cyber-vpn.net',
) {
  return {
    headers: new Headers({
      origin,
      referer: `${origin}/en-EN/pricing`,
    }),
    json: vi.fn().mockResolvedValue(body),
    nextUrl: {
      origin: nextOrigin,
    },
  };
}

describe('POST /api/analytics/traffic', () => {
  beforeEach(() => {
    metricsDistribution.mockClear();
    addBreadcrumb.mockClear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('accepts valid acquisition payloads and records metrics', async () => {
    const response = await POST(
      createRequest({
        connectionType: '4g',
        ctaHref: '/download',
        ctaId: 'download',
        ctaZone: 'landing_hero',
        deviceBucket: 'desktop',
        event: 'cta_click',
        locale: 'ru-RU',
        path: '/ru-RU/pricing',
        reducedMotion: 'no-preference',
        routeGroup: 'marketing',
        saveData: 'off',
        sourceName: 'chatgpt',
        sourceType: 'ai',
        utmCampaign: 'launch',
        utmContent: 'hero',
        utmMedium: 'answer',
        utmSource: 'chatgpt',
        utmTerm: 'vpn',
        viewportBucket: 'desktop',
      }) as never,
    );

    expect(response.status).toBe(204);
    expect(metricsDistribution).toHaveBeenCalledWith(
      'acquisition.cta_click',
      1,
      expect.objectContaining({
        attributes: expect.objectContaining({
          cta_id: 'download',
          cta_zone: 'landing_hero',
          locale: 'ru-RU',
          source_name: 'chatgpt',
          source_type: 'ai',
          utm_content: 'hero',
          utm_term: 'vpn',
        }),
        unit: 'none',
      }),
    );
    expect(addBreadcrumb).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'acquisition',
        data: expect.objectContaining({
          ctaId: 'download',
          ctaZone: 'landing_hero',
        }),
      }),
    );
  });

  it('accepts the customer cabinet origin when the route is served behind another origin', async () => {
    const response = await POST(
      createRequest(
        {
          connectionType: '4g',
          deviceBucket: 'desktop',
          event: 'page_view',
          path: '/ru-RU/login',
          reducedMotion: 'no-preference',
          routeGroup: 'auth',
          saveData: 'off',
          sourceName: 'direct',
          sourceType: 'direct',
          viewportBucket: 'desktop',
        },
        'https://my.cyber-vpn.net',
        'https://cyber-vpn.net',
      ) as never,
    );

    expect(response.status).toBe(204);
    expect(metricsDistribution).toHaveBeenCalled();
  });

  it('accepts custom loopback ports used by local browser smokes', async () => {
    const response = await POST(
      createRequest(
        {
          connectionType: '4g',
          deviceBucket: 'desktop',
          event: 'page_view',
          path: '/ru-RU/pricing',
          reducedMotion: 'no-preference',
          routeGroup: 'marketing',
          saveData: 'off',
          sourceName: 'direct',
          sourceType: 'direct',
          viewportBucket: 'desktop',
        },
        'http://127.0.0.1:9464',
        'http://localhost:3000',
      ) as never,
    );

    expect(response.status).toBe(204);
    expect(metricsDistribution).toHaveBeenCalled();
  });

  it('rejects custom loopback origins in production', async () => {
    vi.stubEnv('NODE_ENV', 'production');

    const response = await POST(
      createRequest(
        {
          connectionType: '4g',
          deviceBucket: 'desktop',
          event: 'page_view',
          path: '/ru-RU/pricing',
          reducedMotion: 'no-preference',
          routeGroup: 'marketing',
          saveData: 'off',
          sourceName: 'direct',
          sourceType: 'direct',
          viewportBucket: 'desktop',
        },
        'http://127.0.0.1:9464',
        'https://cyber-vpn.net',
      ) as never,
    );

    expect(response.status).toBe(403);
    expect(metricsDistribution).not.toHaveBeenCalled();
  });

  it('rejects foreign origins', async () => {
    const response = await POST(
      createRequest(
        {
          connectionType: '4g',
          deviceBucket: 'desktop',
          event: 'page_view',
          path: '/ru-RU/pricing',
          reducedMotion: 'no-preference',
          routeGroup: 'marketing',
          saveData: 'off',
          sourceName: 'google',
          sourceType: 'search',
          viewportBucket: 'desktop',
        },
        'https://evil.example',
        'https://cyber-vpn.net',
      ) as never,
    );

    expect(response.status).toBe(403);
    expect(metricsDistribution).not.toHaveBeenCalled();
  });
});
