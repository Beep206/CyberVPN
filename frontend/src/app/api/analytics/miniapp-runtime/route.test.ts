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
  origin = 'https://cyber-vpn.net',
  nextOrigin = 'https://cyber-vpn.net',
) {
  return {
    headers: new Headers({
      origin,
      referer: `${origin}/ru-RU/miniapp/home`,
    }),
    json: vi.fn().mockResolvedValue(body),
    nextUrl: {
      origin: nextOrigin,
    },
  };
}

describe('POST /api/analytics/miniapp-runtime', () => {
  beforeEach(() => {
    metricsDistribution.mockClear();
    addBreadcrumb.mockClear();
  });

  it('accepts valid Mini App runtime events', async () => {
    const response = await POST(
      createRequest({
        event: 'miniapp_config_loaded',
        page: 'profile',
        locale: 'ru-RU',
        path: '/ru-RU/miniapp/profile',
        checkoutFlow: 'checkout',
        connectionType: '4g',
        configSource: 'remnawave_generated',
        deviceBucket: 'mobile-touch',
        reducedMotion: 'no-preference',
        routeGroup: 'miniapp',
        saveData: 'off',
        viewportBucket: 'mobile-regular',
        paymentStatus: 'completed',
        primaryCtaKind: 'start_trial',
        subscriptionStatus: 'none',
      }) as never,
    );

    expect(response.status).toBe(204);
    expect(metricsDistribution).toHaveBeenCalledWith(
      'miniapp.runtime_event',
      1,
      expect.objectContaining({
        attributes: expect.objectContaining({
          checkout_flow: 'checkout',
          config_source: 'remnawave_generated',
          event: 'miniapp_config_loaded',
          locale: 'ru-RU',
          page: 'profile',
          payment_status: 'completed',
          primary_cta_kind: 'start_trial',
          subscription_status: 'none',
        }),
        unit: 'none',
      }),
    );
    expect(addBreadcrumb).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'miniapp',
        message: 'miniapp_config_loaded',
      }),
    );
  });

  it('accepts the customer cabinet origin when the route is served behind another origin', async () => {
    const response = await POST(
      createRequest(
        {
          event: 'miniapp_opened',
          page: 'home',
          locale: 'ru-RU',
          path: '/ru-RU/miniapp/home',
          connectionType: '4g',
          deviceBucket: 'mobile-touch',
          reducedMotion: 'no-preference',
          routeGroup: 'miniapp',
          saveData: 'off',
          viewportBucket: 'mobile-regular',
        },
        'https://my.cyber-vpn.net',
        'https://cyber-vpn.net',
      ) as never,
    );

    expect(response.status).toBe(204);
    expect(metricsDistribution).toHaveBeenCalled();
  });

  it('keeps the dedicated Mini App VPN page dimension', async () => {
    const response = await POST(
      createRequest({
        event: 'miniapp_config_loaded',
        page: 'vpn',
        locale: 'ru-RU',
        path: '/ru-RU/miniapp/vpn',
        connectionType: '4g',
        configSource: 'remnawave_generated',
        deviceBucket: 'mobile-touch',
        reducedMotion: 'no-preference',
        routeGroup: 'miniapp',
        saveData: 'off',
        viewportBucket: 'mobile-regular',
        subscriptionStatus: 'config_available',
      }) as never,
    );

    expect(response.status).toBe(204);
    expect(metricsDistribution).toHaveBeenCalledWith(
      'miniapp.runtime_event',
      1,
      expect.objectContaining({
        attributes: expect.objectContaining({
          event: 'miniapp_config_loaded',
          page: 'vpn',
          path: '/ru-RU/miniapp/vpn',
        }),
      }),
    );
  });

  it('rejects foreign origins', async () => {
    const response = await POST(
      createRequest(
        {
          event: 'miniapp_opened',
          page: 'home',
          locale: 'ru-RU',
          path: '/ru-RU/miniapp/home',
          connectionType: '4g',
          deviceBucket: 'mobile-touch',
          reducedMotion: 'no-preference',
          routeGroup: 'miniapp',
          saveData: 'off',
          viewportBucket: 'mobile-regular',
        },
        'https://evil.example',
      ) as never,
    );

    expect(response.status).toBe(403);
    expect(metricsDistribution).not.toHaveBeenCalled();
  });
});
