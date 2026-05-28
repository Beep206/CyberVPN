import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { clientCapabilitiesApi } from '../client-capabilities';

const API_BASE = '*/api/v1';

describe('clientCapabilitiesApi', () => {
  it('loads runtime client capabilities', async () => {
    server.use(
      http.get(`${API_BASE}/client/capabilities`, () =>
        HttpResponse.json({
          auth: {
            email_password: true,
            magic_link: true,
            telegram: true,
          },
          payments: {
            web_checkout: false,
            telegram_stars: true,
            cryptobot: false,
            manual_invoice: true,
            autorenewal: false,
          },
          growth: {
            invites: true,
            referral: true,
            promo_codes: true,
            gift_codes: true,
            checkout_code_discounts: true,
            growth_hub: true,
          },
          subscriptions: {
            multi_subscription: true,
            selected_subscription_required: true,
            addons: true,
            upgrade: true,
            trial: true,
            paid_provisioning: true,
          },
          partner: {
            portal: true,
            applications: true,
            codes: true,
            attribution: true,
            storefronts: true,
            reporting: true,
            settlement_sandbox: true,
            webhooks: true,
            payouts: false,
            event_backbone: true,
          },
        }),
      ),
    );

    const response = await clientCapabilitiesApi.get();

    expect(response.data.growth.referral).toBe(true);
    expect(response.data.payments.web_checkout).toBe(false);
    expect(response.data.payments.manual_invoice).toBe(true);
    expect(response.data.partner.payouts).toBe(false);
  });
});
