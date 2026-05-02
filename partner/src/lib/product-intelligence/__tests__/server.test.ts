// @vitest-environment node

import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  buildPartnerProductIntelligenceBootstrap,
  capturePartnerProductEvent,
} from '@/lib/product-intelligence/server';

const { captureMock, getAllFlagsMock, shutdownMock } = vi.hoisted(() => ({
  captureMock: vi.fn(),
  getAllFlagsMock: vi.fn(),
  shutdownMock: vi.fn(),
}));

vi.mock('posthog-node', () => ({
  PostHog: vi.fn().mockImplementation(function MockPostHog() {
    return {
      capture: captureMock,
      getAllFlags: getAllFlagsMock,
      shutdown: shutdownMock,
    };
  }),
}));

describe('product-intelligence server helpers', () => {
  const originalEnv = {
    NEXT_PUBLIC_POSTHOG_HOST: process.env.NEXT_PUBLIC_POSTHOG_HOST,
    NEXT_PUBLIC_POSTHOG_TOKEN: process.env.NEXT_PUBLIC_POSTHOG_TOKEN,
    POSTHOG_HOST: process.env.POSTHOG_HOST,
    POSTHOG_PERSONAL_API_KEY: process.env.POSTHOG_PERSONAL_API_KEY,
    POSTHOG_PROJECT_API_KEY: process.env.POSTHOG_PROJECT_API_KEY,
  };

  beforeEach(() => {
    captureMock.mockReset();
    getAllFlagsMock.mockReset();
    shutdownMock.mockReset();

    process.env.POSTHOG_HOST = originalEnv.POSTHOG_HOST;
    process.env.POSTHOG_PERSONAL_API_KEY = originalEnv.POSTHOG_PERSONAL_API_KEY;
    process.env.POSTHOG_PROJECT_API_KEY = originalEnv.POSTHOG_PROJECT_API_KEY;
    process.env.NEXT_PUBLIC_POSTHOG_HOST = originalEnv.NEXT_PUBLIC_POSTHOG_HOST;
    process.env.NEXT_PUBLIC_POSTHOG_TOKEN = originalEnv.NEXT_PUBLIC_POSTHOG_TOKEN;
  });

  it('stays disabled when server config is missing', async () => {
    delete process.env.POSTHOG_HOST;
    delete process.env.POSTHOG_PROJECT_API_KEY;
    delete process.env.NEXT_PUBLIC_POSTHOG_HOST;
    delete process.env.NEXT_PUBLIC_POSTHOG_TOKEN;

    await expect(capturePartnerProductEvent({
      distinctId: 'user_42',
      event: 'partner_dashboard_viewed',
      properties: {
        path: '/ru-RU/dashboard',
        route_group: 'dashboard',
        surface: 'partner_portal',
      },
    })).resolves.toEqual({
      reason: 'missing_server_config',
      status: 'disabled',
    });
    expect(captureMock).not.toHaveBeenCalled();
  });

  it('captures sanitized events through posthog-node when configured', async () => {
    process.env.POSTHOG_HOST = 'https://posthog.internal';
    process.env.POSTHOG_PROJECT_API_KEY = 'ph_project_token';

    await expect(capturePartnerProductEvent({
      distinctId: 'user_42',
      event: 'partner_dashboard_viewed',
      properties: {
        locale: 'ru-RU',
        path: '/ru-RU/dashboard',
        route_group: 'dashboard',
        surface: 'partner_portal',
      },
    })).resolves.toEqual({
      status: 'captured',
    });

    expect(captureMock).toHaveBeenCalledWith({
      distinctId: 'user_42',
      event: 'partner_dashboard_viewed',
      properties: {
        locale: 'ru-RU',
        path: '/ru-RU/dashboard',
        route_group: 'dashboard',
        surface: 'partner_portal',
      },
    });
    expect(shutdownMock).toHaveBeenCalledTimes(1);
  });

  it('falls back to default-off bootstrap without a distinct id', async () => {
    process.env.POSTHOG_HOST = 'https://posthog.internal';
    process.env.POSTHOG_PROJECT_API_KEY = 'ph_project_token';

    await expect(buildPartnerProductIntelligenceBootstrap()).resolves.toEqual(
      expect.objectContaining({
        distinctId: null,
        evaluationSource: 'fallback',
        flags: {
          partner_portal_dashboard_spotlight_v1: false,
          partner_portal_realtime_workspace_feed_v1: false,
        },
      }),
    );
    expect(getAllFlagsMock).not.toHaveBeenCalled();
  });

  it('coerces server-evaluated flags into the governed bootstrap contract', async () => {
    process.env.POSTHOG_HOST = 'https://posthog.internal';
    process.env.POSTHOG_PROJECT_API_KEY = 'ph_project_token';
    getAllFlagsMock.mockResolvedValue({
      ignored_flag: true,
      partner_portal_dashboard_spotlight_v1: true,
      partner_portal_realtime_workspace_feed_v1: false,
    });

    await expect(buildPartnerProductIntelligenceBootstrap({ distinctId: 'user_42' })).resolves.toEqual(
      expect.objectContaining({
        distinctId: 'user_42',
        evaluationSource: 'server_evaluated',
        flags: {
          partner_portal_dashboard_spotlight_v1: true,
          partner_portal_realtime_workspace_feed_v1: false,
        },
      }),
    );
    expect(getAllFlagsMock).toHaveBeenCalledWith('user_42');
  });
});
