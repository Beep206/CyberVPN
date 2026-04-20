import { beforeEach, describe, expect, it, vi } from 'vitest';
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
  origin = 'https://vpn.ozoxy.ru',
  nextOrigin = 'https://vpn.ozoxy.ru',
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
        'https://vpn.ozoxy.ru',
      ) as never,
    );

    expect(response.status).toBe(403);
    expect(metricsDistribution).not.toHaveBeenCalled();
  });
});
