// @vitest-environment node

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { POST } from './route';

const { addBreadcrumb, metricsDistribution } = vi.hoisted(() => ({
  addBreadcrumb: vi.fn(),
  metricsDistribution: vi.fn(),
}));

const { capturePartnerProductEvent } = vi.hoisted(() => ({
  capturePartnerProductEvent: vi.fn(),
}));

vi.mock('@sentry/nextjs', () => ({
  addBreadcrumb,
  metrics: {
    distribution: metricsDistribution,
  },
}));

vi.mock('@/lib/product-intelligence/server', () => ({
  capturePartnerProductEvent,
}));

function createRequest(
  body: unknown,
  origin = 'https://partner.ozoxy.ru',
  nextOrigin = 'https://partner.ozoxy.ru',
) {
  return {
    headers: new Headers({
      origin,
      referer: `${origin}/ru-RU/dashboard`,
    }),
    json: vi.fn().mockResolvedValue(body),
    nextUrl: {
      origin: nextOrigin,
    },
  };
}

describe('POST /api/analytics/product-events', () => {
  beforeEach(() => {
    addBreadcrumb.mockClear();
    capturePartnerProductEvent.mockReset();
    metricsDistribution.mockClear();
  });

  it('accepts sanitized product analytics payloads', async () => {
    capturePartnerProductEvent.mockResolvedValue({ status: 'captured' });

    const response = await POST(createRequest({
      distinctId: 'user_42',
      event: 'partner_dashboard_viewed',
      properties: {
        ignored_property: 'drop_me',
        locale: 'ru-RU',
        path: '/ru-RU/dashboard',
        route_group: 'dashboard',
        surface: 'partner_portal',
      },
    }) as never);

    expect(response.status).toBe(204);
    expect(capturePartnerProductEvent).toHaveBeenCalledWith({
      distinctId: 'user_42',
      event: 'partner_dashboard_viewed',
      properties: {
        locale: 'ru-RU',
        path: '/ru-RU/dashboard',
        route_group: 'dashboard',
        surface: 'partner_portal',
      },
    });
    expect(metricsDistribution).toHaveBeenCalledWith(
      'product_intelligence.capture',
      1,
      expect.objectContaining({
        attributes: expect.objectContaining({
          delivery_status: 'captured',
          event: 'partner_dashboard_viewed',
          source_class: 'frontend_sdk',
        }),
      }),
    );
  });

  it('rejects foreign origins', async () => {
    const response = await POST(
      createRequest(
        {
          distinctId: 'user_42',
          event: 'partner_dashboard_viewed',
          properties: {
            path: '/ru-RU/dashboard',
            route_group: 'dashboard',
            surface: 'partner_portal',
          },
        },
        'https://evil.example',
        'https://partner.ozoxy.ru',
      ) as never,
    );

    expect(response.status).toBe(403);
    expect(capturePartnerProductEvent).not.toHaveBeenCalled();
  });

  it('rejects invalid payloads before bridge delivery', async () => {
    const response = await POST(createRequest({
      distinctId: '',
      event: 'not_allowed',
    }) as never);

    expect(response.status).toBe(400);
    expect(capturePartnerProductEvent).not.toHaveBeenCalled();
  });
});
