import { describe, expect, it } from 'vitest';
import { getPlanPrice, type SubscriptionPlan } from '../plan-presenter';

const plan: SubscriptionPlan = {
  uuid: 'plan-plus-365',
  name: 'plus_365',
  plan_code: 'plus',
  display_name: 'Plus',
  catalog_visibility: 'public',
  duration_days: 365,
  traffic_limit_bytes: null,
  devices_included: 5,
  price_usd: 79,
  price_rub: 7901,
  traffic_policy: {
    mode: 'fair_use',
    display_label: 'Unlimited',
    enforcement_profile: null,
  },
  connection_modes: ['standard', 'stealth'],
  server_pool: ['shared_plus'],
  support_sla: 'standard',
  dedicated_ip: {
    included: 0,
    eligible: true,
  },
  sale_channels: ['web'],
  invite_bundle: {
    count: 2,
    friend_days: 14,
    expiry_days: 60,
  },
  trial_eligible: false,
  features: {},
  is_active: true,
  sort_order: 10,
};

describe('subscription plan-presenter backend catalog price rule', () => {
  it('uses backend catalog money when a commercial catalog price is present', () => {
    const price = getPlanPrice({
      ...plan,
      public_catalog_price: {
        amount: '79',
        currency: 'EUR',
        minorUnits: 2,
      },
    }, 'ru-RU');

    expect(price.currency).toBe('EUR');
    expect(price.amount).toBe(79);
    expect(price.formatted).toContain('79');
    expect(price.localEstimate).toBeNull();
  });
});
