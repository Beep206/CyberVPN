// @vitest-environment node

import { describe, expect, it } from 'vitest';
import {
  buildCheckoutPaymentSubmittedCapture,
  buildCheckoutStartedCapture,
  buildCheckoutStepCompletedCapture,
  buildCheckoutStepViewedCapture,
  buildOnboardingStartedCapture,
  buildOnboardingStepCompletedCapture,
} from '@/lib/product-intelligence/event-builders';

describe('product analytics event builders', () => {
  it('builds checkout capture payloads with canonical storefront routing metadata', () => {
    expect(buildCheckoutStartedCapture({
      distinctId: 'user_42',
      locale: 'ru-RU',
      path: '/ru-RU/checkout',
      pricebookKey: 'starter-usd',
      saleChannel: 'partner_storefront',
      storefrontKey: 'storefront_ru',
    })).toEqual({
      distinctId: 'user_42',
      event: 'checkout_started',
      properties: {
        checkout_surface: 'storefront',
        locale: 'ru-RU',
        path: '/ru-RU/checkout',
        pricebook_key: 'starter-usd',
        route_group: 'storefront_checkout',
        sale_channel: 'partner_storefront',
        storefront_key: 'storefront_ru',
      },
    });

    expect(buildCheckoutStepViewedCapture({
      distinctId: 'user_42',
      locale: 'ru-RU',
      path: '/ru-RU/checkout',
      step: 'catalog',
      storefrontKey: 'storefront_ru',
    }).event).toBe('checkout_step_viewed');

    expect(buildCheckoutStepCompletedCapture({
      distinctId: 'user_42',
      locale: 'ru-RU',
      path: '/ru-RU/checkout',
      step: 'order_ready',
      storefrontKey: 'storefront_ru',
    }).properties?.step).toBe('order_ready');
  });

  it('builds checkout submission captures from governed storefront inputs', () => {
    expect(buildCheckoutPaymentSubmittedCapture({
      currencyCode: 'EUR',
      distinctId: 'user_42',
      flow: 'new_purchase',
      locale: 'ru-RU',
      offerKey: 'vpn_pro_monthly',
      path: '/ru-RU/checkout',
      pricebookKey: 'starter-usd',
      saleChannel: 'partner_storefront',
      storefrontKey: 'storefront_ru',
    })).toEqual({
      distinctId: 'user_42',
      event: 'checkout_payment_submitted',
      properties: {
        checkout_surface: 'storefront',
        currency_code: 'EUR',
        flow: 'new_purchase',
        locale: 'ru-RU',
        offer_key: 'vpn_pro_monthly',
        path: '/ru-RU/checkout',
        pricebook_key: 'starter-usd',
        route_group: 'storefront_checkout',
        sale_channel: 'partner_storefront',
        storefront_key: 'storefront_ru',
      },
    });
  });

  it('builds onboarding captures from partner application workflow inputs', () => {
    expect(buildOnboardingStartedCapture({
      applicationStatus: 'draft',
      distinctId: 'user_42',
      locale: 'ru-RU',
      path: '/ru-RU/application',
      workspaceStatus: 'draft',
    })).toEqual({
      distinctId: 'user_42',
      event: 'onboarding_started',
      properties: {
        application_status: 'draft',
        locale: 'ru-RU',
        path: '/ru-RU/application',
        route_group: 'application_onboarding',
        surface: 'partner_portal',
        workspace_status: 'draft',
      },
    });

    expect(buildOnboardingStepCompletedCapture({
      applicationStatus: 'needs_info',
      distinctId: 'user_42',
      locale: 'ru-RU',
      path: '/ru-RU/application',
      stage: 'compliance',
      workspaceStatus: 'needs_info',
    }).properties?.stage).toBe('compliance');
  });
});
