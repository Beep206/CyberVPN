import { describe, expect, it } from 'vitest';
import type {
  AddonRecord,
  CurrentEntitlement,
  CurrentServiceState,
  OrderRecord,
  PlanRecord,
} from '../subscription-cabinet-model';
import {
  formatBytes,
  formatDate,
  formatDuration,
  formatLabel,
  getCurrentPlan,
  getDaysUntilExpiry,
  getAddonPrice,
  getOrderStatus,
  getOrderDisplayName,
  getOrderTone,
  getPlanPrice,
  getPlanAction,
  getPublicPlans,
  getSortedOrders,
  getSubscriptionHealth,
  getTrafficLabel,
  getVisibleAddons,
  readEntitlementNumber,
  readEntitlementString,
  readEntitlementStringArray,
} from '../subscription-cabinet-model';

function plan(overrides: Partial<PlanRecord>): PlanRecord {
  const base: PlanRecord = {
    catalog_visibility: 'public',
    connection_modes: ['standard'],
    dedicated_ip: {
      eligible: true,
      included: 0,
    },
    devices_included: 5,
    display_name: 'Pro Plan',
    duration_days: 30,
    features: {},
    invite_bundle: {
      count: 0,
      expiry_days: 0,
      friend_days: 0,
    },
    is_active: true,
    name: 'PRO',
    plan_code: 'pro',
    price_rub: null,
    price_usd: 29,
    sale_channels: ['web'],
    server_pool: ['shared_plus'],
    sort_order: 20,
    support_sla: 'priority',
    traffic_limit_bytes: null,
    traffic_policy: {
      display_label: 'Unlimited',
      enforcement_profile: null,
      mode: 'fair_use',
    },
    trial_eligible: false,
    uuid: 'plan-pro',
  };

  return { ...base, ...overrides };
}

const entitlement: CurrentEntitlement = {
  addons: [],
  display_name: 'Pro Plan',
  effective_entitlements: {
    connection_modes: ['standard', 'stealth'],
    device_limit: '7',
  },
  expires_at: '2026-04-27T00:00:00Z',
  invite_bundle: {},
  is_trial: false,
  period_days: 30,
  plan_code: 'pro',
  plan_uuid: 'plan-pro',
  status: 'active',
};

const serviceState = {
  access_delivery_channel: {},
  provisioning_profile: {},
  service_identity: {},
} as CurrentServiceState;

describe('subscription cabinet model', () => {
  it('reads entitlement values and expiry state safely', () => {
    expect(readEntitlementNumber(entitlement, 'device_limit')).toBe(7);
    expect(readEntitlementNumber(entitlement, 'missing')).toBeNull();
    expect(readEntitlementNumber({
      ...entitlement,
      effective_entitlements: {
        device_limit: 'not-a-number',
      },
    }, 'device_limit')).toBeNull();
    expect(readEntitlementString({
      ...entitlement,
      effective_entitlements: {
        support_sla: ' priority ',
      },
    }, 'support_sla')).toBe('priority');
    expect(readEntitlementString({
      ...entitlement,
      effective_entitlements: {
        support_sla: '   ',
      },
    }, 'support_sla')).toBeNull();
    expect(readEntitlementStringArray(entitlement, 'connection_modes')).toEqual([
      'standard',
      'stealth',
    ]);
    expect(readEntitlementStringArray({
      ...entitlement,
      effective_entitlements: {
        connection_modes: ['standard', '', null, 'stealth'],
      },
    }, 'connection_modes')).toEqual(['standard', 'stealth']);
    expect(readEntitlementStringArray(entitlement, 'missing')).toEqual([]);
    expect(getDaysUntilExpiry(entitlement, new Date('2026-04-24T00:00:00Z'))).toBe(3);
    expect(getDaysUntilExpiry({ ...entitlement, expires_at: null })).toBeNull();
    expect(getDaysUntilExpiry({ ...entitlement, expires_at: 'not-a-date' })).toBeNull();
    expect(formatBytes(1024 ** 3, 'en-EN')).toBe('1 GB');
    expect(formatBytes(0, 'en-EN')).toBe('0 B');
    expect(formatBytes(Number.NaN, 'en-EN')).toBe('0 B');
    expect(formatDate('2026-04-24T00:00:00Z', 'en-EN')).toBe('Apr 24, 2026');
    expect(formatDate(null, 'en-EN')).toBeNull();
    expect(formatDate('not-a-date', 'en-EN')).toBeNull();
  });

  it('derives health from active entitlement, expiry, and provisioning', () => {
    expect(
      getSubscriptionHealth({
        entitlement: {
          ...entitlement,
          expires_at: '2026-05-24T00:00:00Z',
        },
        now: new Date('2026-04-24T00:00:00Z'),
        serviceState,
      }),
    ).toBe('healthy');
    expect(
      getSubscriptionHealth({
        entitlement,
        now: new Date('2026-04-24T00:00:00Z'),
        serviceState,
      }),
    ).toBe('attention');
    expect(
      getSubscriptionHealth({
        entitlement: { ...entitlement, status: 'expired' },
        now: new Date('2026-04-24T00:00:00Z'),
        serviceState,
      }),
    ).toBe('critical');
    expect(
      getSubscriptionHealth({
        entitlement: { ...entitlement, status: 'expired' },
        now: new Date('2026-04-24T00:00:00Z'),
        serviceState,
        trial: {
          days_remaining: 3,
          is_eligible: false,
          is_trial_active: true,
          trial_end: '2026-04-27T00:00:00Z',
          trial_start: '2026-04-24T00:00:00Z',
        },
      }),
    ).toBe('attention');
    expect(
      getSubscriptionHealth({
        entitlement: {
          ...entitlement,
          expires_at: '2026-05-24T00:00:00Z',
        },
        now: new Date('2026-04-24T00:00:00Z'),
        serviceState: null,
      }),
    ).toBe('attention');
    expect(
      getSubscriptionHealth({
        entitlement: {
          ...entitlement,
          expires_at: '2026-05-24T00:00:00Z',
        },
        now: new Date('2026-04-24T00:00:00Z'),
        serviceState: {
          access_delivery_channel: null,
          provisioning_profile: {},
          service_identity: {},
        } as CurrentServiceState,
      }),
    ).toBe('attention');
  });

  it('sorts public plans and maps plan actions against current entitlement', () => {
    const current = plan({ sort_order: 20, uuid: 'plan-pro' });
    const upgrade = plan({ display_name: 'Max Plan', plan_code: 'max', sort_order: 30, uuid: 'plan-max' });
    const downgrade = plan({ display_name: 'Basic Plan', plan_code: 'basic', sort_order: 10, uuid: 'plan-basic' });
    const inactive = plan({ is_active: false, plan_code: 'inactive', uuid: 'plan-inactive' });
    const hidden = plan({ catalog_visibility: 'hidden', plan_code: 'hidden', uuid: 'plan-hidden' });
    const publicPlans = getPublicPlans([upgrade, hidden, inactive, current, downgrade]);

    expect(publicPlans.map((item) => item.uuid)).toEqual([
      'plan-basic',
      'plan-pro',
      'plan-max',
    ]);
    expect(getCurrentPlan(entitlement, publicPlans)?.uuid).toBe('plan-pro');
    expect(
      getCurrentPlan({ ...entitlement, plan_uuid: 'missing', plan_code: 'max' }, publicPlans)
        ?.uuid,
    ).toBe('plan-max');
    expect(getCurrentPlan(null, publicPlans)).toBeNull();
    expect(getPlanAction({ currentPlan: current, entitlement, targetPlan: current })).toBe('current');
    expect(getPlanAction({ currentPlan: current, entitlement, targetPlan: upgrade })).toBe('upgrade');
    expect(getPlanAction({ currentPlan: current, entitlement, targetPlan: downgrade })).toBe('downgrade');
    expect(
      getPlanAction({
        currentPlan: null,
        entitlement: { ...entitlement, status: 'expired' },
        targetPlan: downgrade,
      }),
    ).toBe('purchase');
    expect(
      getPlanAction({
        currentPlan: null,
        entitlement: { ...entitlement, is_trial: true, plan_code: 'trial', plan_uuid: null },
        targetPlan: downgrade,
      }),
    ).toBe('purchase');
  });

  it('filters add-ons by web channel and plan quantity caps', () => {
    const addons: AddonRecord[] = [
      {
        code: 'extra-device',
        delta_entitlements: {},
        display_name: 'Extra device',
        duration_mode: 'subscription_aligned',
        is_active: true,
        is_stackable: true,
        max_quantity_by_plan: { pro: 2 },
        price_rub: null,
        price_usd: 5,
        quantity_step: 1,
        requires_location: false,
        sale_channels: ['web'],
        uuid: 'addon-1',
      },
      {
        code: 'global-addon',
        delta_entitlements: {},
        display_name: 'Global add-on',
        duration_mode: 'subscription_aligned',
        is_active: true,
        is_stackable: true,
        max_quantity_by_plan: {},
        price_rub: 200,
        price_usd: 2,
        quantity_step: 1,
        requires_location: false,
        sale_channels: ['web'],
        uuid: 'addon-3',
      },
      {
        code: 'blocked',
        delta_entitlements: {},
        display_name: 'Blocked',
        duration_mode: 'subscription_aligned',
        is_active: true,
        is_stackable: false,
        max_quantity_by_plan: { pro: 0 },
        price_rub: null,
        price_usd: 1,
        quantity_step: 1,
        requires_location: false,
        sale_channels: ['web'],
        uuid: 'addon-2',
      },
      {
        code: 'bot-only',
        delta_entitlements: {},
        display_name: 'Bot only',
        duration_mode: 'subscription_aligned',
        is_active: true,
        is_stackable: true,
        max_quantity_by_plan: {},
        price_rub: null,
        price_usd: 3,
        quantity_step: 1,
        requires_location: false,
        sale_channels: ['telegram'],
        uuid: 'addon-4',
      },
    ];

    expect(getVisibleAddons(addons, 'pro').map((addon) => addon.code)).toEqual([
      'global-addon',
      'extra-device',
    ]);
    expect(getVisibleAddons(addons, null).map((addon) => addon.code)).toEqual([
      'blocked',
      'global-addon',
      'extra-device',
    ]);
    expect(getAddonPrice(addons[0], 'en-EN')).toBe('$5');
    expect(getAddonPrice(addons[1], 'ru-RU').replace(/\u00a0/g, ' ')).toBe('200 ₽');
  });

  it('formats order display and status tone without exposing provider internals', () => {
    const order = {
      currency_code: 'USD',
      created_at: '2026-04-24T10:00:00Z',
      displayed_price: 29,
      id: 'order-paid-123456',
      items: [{ display_name: 'Pro Plan' }],
      order_status: 'committed',
      settlement_status: 'paid',
      subscription_plan_id: 'plan-pro',
    } as OrderRecord;

    expect(getOrderDisplayName(order, [])).toBe('Pro Plan');
    expect(getOrderDisplayName({ ...order, items: [] }, [plan({ uuid: 'plan-pro' })])).toBe('Pro Plan');
    expect(getOrderDisplayName({ ...order, items: [], subscription_plan_id: 'missing' }, [])).toBe(
      'Order order-pa',
    );
    expect(getOrderStatus(order)).toBe('paid');
    expect(getOrderStatus({ ...order, settlement_status: '' })).toBe('committed');
    expect(getOrderTone(order)).toBe('green');
    expect(getOrderTone({ ...order, order_status: 'awaiting_payment', settlement_status: '' })).toBe('cyan');
    expect(getOrderTone({ ...order, order_status: 'refund_pending', settlement_status: '' })).toBe('purple');
    expect(getOrderTone({ ...order, order_status: 'manual_review', settlement_status: '' })).toBe('amber');
    expect(
      getSortedOrders([
        { ...order, created_at: '2026-04-24T10:00:00Z', id: 'older' },
        { ...order, created_at: '2026-04-25T10:00:00Z', id: 'newer' },
      ]).map((item) => item.id),
    ).toEqual(['newer', 'older']);
  });

  it('formats plan prices, durations, labels and traffic policies', () => {
    const rubPlan = plan({
      price_rub: 990,
      price_usd: 9,
      traffic_limit_bytes: 1024 ** 4,
      traffic_policy: {
        display_label: '',
        enforcement_profile: null,
        mode: 'quota',
      },
    });
    const usdPlan = plan({
      price_rub: 0,
      price_usd: 19.99,
      traffic_limit_bytes: null,
      traffic_policy: {
        display_label: '',
        enforcement_profile: null,
        mode: 'fair_use',
      },
    });
    const labeledPlan = plan({
      traffic_policy: {
        display_label: '2 TB fair-use',
        enforcement_profile: null,
        mode: 'fair_use',
      },
    });

    const rubPrice = getPlanPrice(rubPlan, 'ru-RU');
    const fallbackUsdPrice = getPlanPrice(usdPlan, 'ru-RU');

    expect(rubPrice).toMatchObject({
      amount: 990,
      currency: 'RUB',
    });
    expect(rubPrice.formatted.replace(/\u00a0/g, ' ')).toBe('990 ₽');
    expect(fallbackUsdPrice).toMatchObject({
      amount: 19.99,
      currency: 'USD',
    });
    expect(fallbackUsdPrice.formatted.replace(/\u00a0/g, ' ')).toBe('19,99 $');
    expect(formatDuration(1)).toBe('1 day');
    expect(formatDuration(30)).toBe('30 days');
    expect(formatLabel('manual_review-required', 'Fallback')).toBe('Manual Review Required');
    expect(formatLabel('   ', 'Fallback')).toBe('Fallback');
    expect(getTrafficLabel(labeledPlan)).toBe('2 TB fair-use');
    expect(getTrafficLabel(rubPlan, 'en-EN')).toBe('1 TB');
    expect(getTrafficLabel(usdPlan, 'en-EN')).toBe('Unlimited');
  });
});
