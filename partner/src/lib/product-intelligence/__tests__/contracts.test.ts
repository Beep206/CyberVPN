// @vitest-environment node

import { describe, expect, it } from 'vitest';
import {
  buildDefaultFeatureFlagBootstrap,
  coerceProductFeatureFlagSnapshot,
  PRODUCT_ANALYTICS_EVENT_DEFINITIONS,
  sanitizeProductAnalyticsCapture,
} from '@/lib/product-intelligence/contracts';

describe('product-intelligence contracts', () => {
  it('defaults all governed product flags to off', () => {
    expect(buildDefaultFeatureFlagBootstrap('user_42')).toEqual(
      expect.objectContaining({
        distinctId: 'user_42',
        evaluationSource: 'fallback',
        flags: {
          partner_portal_dashboard_spotlight_v1: false,
          partner_portal_realtime_workspace_feed_v1: false,
        },
      }),
    );
  });

  it('coerces only governed boolean flags from raw PostHog responses', () => {
    expect(coerceProductFeatureFlagSnapshot({
      partner_portal_dashboard_spotlight_v1: true,
      partner_portal_realtime_workspace_feed_v1: 'variant',
    })).toEqual({
      partner_portal_dashboard_spotlight_v1: true,
      partner_portal_realtime_workspace_feed_v1: false,
    });
  });

  it('sanitizes payloads against the canonical allowlist', () => {
    expect(sanitizeProductAnalyticsCapture({
      distinctId: 'user_42',
      event: 'feature_flag_evaluated',
      properties: {
        evaluation_source: 'server_evaluated',
        flag_key: 'partner_portal_dashboard_spotlight_v1',
        flag_value: 'on',
        locale: 'ru-RU',
        path: '/ru-RU/dashboard',
        route_group: 'dashboard',
        workspace_status: 'blocked',
      },
    })).toEqual({
      distinctId: 'user_42',
      event: 'feature_flag_evaluated',
      properties: {
        evaluation_source: 'server_evaluated',
        flag_key: 'partner_portal_dashboard_spotlight_v1',
        flag_value: 'on',
        locale: 'ru-RU',
        path: '/ru-RU/dashboard',
        route_group: 'dashboard',
      },
    });
  });

  it('includes the P3.7 checkout, onboarding, and retention event families in the governed catalog', () => {
    expect(PRODUCT_ANALYTICS_EVENT_DEFINITIONS.checkout_started.sourceClass).toBe('frontend_sdk');
    expect(PRODUCT_ANALYTICS_EVENT_DEFINITIONS.onboarding_step_completed.sourceClass).toBe('frontend_sdk');
    expect(PRODUCT_ANALYTICS_EVENT_DEFINITIONS.subscription_activated.sourceClass).toBe('nats_bridge');
  });
});
