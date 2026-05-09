import { describe, expect, it } from 'vitest';
import {
  formatBytes,
  formatDate,
  formatDateTime,
  formatMoney,
  getCabinetActionIds,
  getCabinetHealth,
  getServiceAccessLabel,
  getStage1DashboardStates,
  getUsagePercentage,
  readEntitlementNumber,
  readEntitlementString,
  readEntitlementStringArray,
  type CurrentEntitlementState,
  type CurrentServiceState,
  type UsageResponse,
} from '../customer-cabinet-model';
import type { GrowthNotificationCounters } from '@/lib/api/growth-notifications';

const entitlement: CurrentEntitlementState = {
  addons: [],
  display_name: 'Pro',
  effective_entitlements: {
    connection_modes: ['wireguard', 'stealth'],
    device_limit: '5',
    display_traffic_label: '2 TB',
  },
  expires_at: '2026-05-24T00:00:00Z',
  invite_bundle: {},
  is_trial: false,
  period_days: 30,
  plan_code: 'pro',
  plan_uuid: 'plan-1',
  status: 'active',
};

const usage: UsageResponse = {
  bandwidth_limit_bytes: 100,
  bandwidth_used_bytes: 50,
  connections_active: 1,
  connections_limit: 5,
  generated_at: '2026-04-24T10:00:05Z',
  last_connection_at: '2026-04-24T10:00:00Z',
  period_end: '2026-05-24T00:00:00Z',
  period_start: '2026-04-24T00:00:00Z',
  usage_available: true,
  usage_source: 'remnawave',
  usage_unavailable_reason: null,
};

const serviceState: CurrentServiceState = {
  access_delivery_channel: {
    archived_at: null,
    archived_by_admin_user_id: null,
    archive_reason_code: null,
    auth_realm_id: 'realm-1',
    channel_status: 'active',
    channel_subject_ref: 'web',
    channel_type: 'shared_client',
    created_at: '2026-04-24T00:00:00Z',
    delivery_context: {},
    delivery_key: 'delivery-1',
    delivery_payload: {},
    device_credential_id: 'credential-1',
    id: 'channel-1',
    last_accessed_at: null,
    last_delivered_at: null,
    origin_storefront_id: null,
    provider_name: 'remnawave',
    provisioning_profile_id: 'profile-1',
    service_identity_id: 'service-1',
    updated_at: '2026-04-24T00:00:00Z',
  },
  auth_realm_id: 'realm-1',
  consumption_context: {},
  customer_account_id: 'customer-1',
  device_credential: {
    auth_realm_id: 'realm-1',
    created_at: '2026-04-24T00:00:00Z',
    credential_context: {},
    credential_key: 'credential-1',
    credential_status: 'active',
    credential_type: 'desktop_client',
    id: 'credential-1',
    issued_at: '2026-04-24T00:00:00Z',
    last_used_at: null,
    origin_storefront_id: null,
    provider_credential_ref: null,
    provider_name: 'remnawave',
    provisioning_profile_id: 'profile-1',
    revoked_at: null,
    revoked_by_admin_user_id: null,
    revoke_reason_code: null,
    service_identity_id: 'service-1',
    subject_key: 'official-web-dashboard',
    updated_at: '2026-04-24T00:00:00Z',
  },
  entitlement_snapshot: entitlement,
  provider_name: 'remnawave',
  provisioning_profile: {
    created_at: '2026-04-24T00:00:00Z',
    delivery_method: 'client',
    id: 'profile-1',
    profile_key: 'default',
    profile_status: 'active',
    provider_name: 'remnawave',
    provider_profile_ref: null,
    provisioning_payload: {},
    service_identity_id: 'service-1',
    target_channel: 'shared_client',
    updated_at: '2026-04-24T00:00:00Z',
  },
  purchase_context: {},
  service_identity: {
    auth_realm_id: 'realm-1',
    created_at: '2026-04-24T00:00:00Z',
    customer_account_id: 'customer-1',
    id: 'service-1',
    identity_status: 'active',
    origin_storefront_id: null,
    provider_name: 'remnawave',
    provider_subject_ref: null,
    service_context: {},
    service_key: 'service-1',
    source_order_id: null,
    updated_at: '2026-04-24T00:00:00Z',
  },
};

const notifications: GrowthNotificationCounters = {
  action_required_notifications: 0,
  total_notifications: 2,
  unread_notifications: 1,
};

describe('customer cabinet model', () => {
  it('reads typed entitlement values defensively', () => {
    expect(readEntitlementNumber(entitlement, 'device_limit')).toBe(5);
    expect(readEntitlementString(entitlement, 'display_traffic_label')).toBe(
      '2 TB',
    );
    expect(readEntitlementStringArray(entitlement, 'connection_modes')).toEqual([
      'wireguard',
      'stealth',
    ]);
  });

  it('formats bytes, dates, money, service channels, and usage percentage', () => {
    expect(formatBytes(1536, 'en-US')).toBe('1.5 KB');
    expect(formatDate('2026-04-24T00:00:00Z', 'en-US')).toBe('Apr 24, 2026');
    expect(formatDateTime('2026-04-24T10:30:00Z', 'en-US')).toContain(
      'Apr 24, 2026',
    );
    expect(formatMoney(12.5, 'USD', 'en-US')).toBe('$12.50');
    expect(getServiceAccessLabel('shared_client', 'Pending')).toBe(
      'Shared Client',
    );
    expect(getUsagePercentage(usage)).toBe(50);
    expect(
      getUsagePercentage({
        ...usage,
        usage_available: false,
        usage_source: 'unavailable',
        usage_unavailable_reason: 'upstream_unavailable',
      }),
    ).toBeNull();
  });

  it('marks a complete account as healthy', () => {
    expect(
      getCabinetHealth({
        entitlement,
        notifications,
        serviceState,
        usage,
        now: new Date('2026-04-24T00:00:00Z'),
      }),
    ).toBe('healthy');
  });

  it('derives S1 dashboard state cards for active paid access', () => {
    expect(
      getStage1DashboardStates({
        entitlement,
        serviceState,
        trial: null,
        now: new Date('2026-04-24T00:00:00Z'),
      }),
    ).toEqual([
      {
        actionId: 'getConfig',
        id: 'access',
        state: 'active',
        tone: 'green',
      },
      {
        actionId: null,
        id: 'payment',
        state: 'paid',
        tone: 'green',
      },
      {
        actionId: 'getConfig',
        id: 'provisioning',
        state: 'ready',
        tone: 'green',
      },
    ]);
  });

  it('uses neutral S1 checking states before entitlement data is known', () => {
    expect(getStage1DashboardStates({}).map((state) => [state.id, state.state, state.actionId])).toEqual([
      ['access', 'checking', null],
      ['payment', 'checking', null],
      ['provisioning', 'checking', null],
    ]);
  });

  it('keeps grace period as attention instead of critical', () => {
    const graceEntitlement: CurrentEntitlementState = {
      ...entitlement,
      expires_at: '2026-04-23T00:00:00Z',
      status: 'grace_period',
    };

    expect(
      getCabinetHealth({
        entitlement: graceEntitlement,
        notifications,
        serviceState,
        usage,
        now: new Date('2026-04-24T00:00:00Z'),
      }),
    ).toBe('attention');

    expect(
      getStage1DashboardStates({
        entitlement: graceEntitlement,
        serviceState,
        now: new Date('2026-04-24T00:00:00Z'),
      })[0],
    ).toMatchObject({
      actionId: 'managePlan',
      id: 'access',
      state: 'grace',
      tone: 'amber',
    });
  });

  it('renders trial, payment failure, and provisioning failure states explicitly', () => {
    expect(
      getStage1DashboardStates({
        entitlement: { ...entitlement, is_trial: true, status: 'trial_active' },
        serviceState,
        trial: {
          days_remaining: 2,
          is_eligible: false,
          is_trial_active: true,
          trial_end: '2026-04-26T00:00:00Z',
          trial_start: '2026-04-24T00:00:00Z',
        },
      }).map((state) => [state.id, state.state, state.tone]),
    ).toEqual([
      ['access', 'trial_active', 'green'],
      ['payment', 'not_started', 'cyan'],
      ['provisioning', 'ready', 'green'],
    ]);

    expect(
      getStage1DashboardStates({
        entitlement: {
          ...entitlement,
          effective_entitlements: {
            stage1_payment_state: 'failed',
            stage1_provisioning_state: 'failed',
          },
        },
        serviceState,
      }).map((state) => [state.id, state.state, state.actionId]),
    ).toEqual([
      ['access', 'active', 'getConfig'],
      ['payment', 'failed', 'managePlan'],
      ['provisioning', 'failed', 'finishProvisioning'],
    ]);
  });

  it('does not degrade health before service state is known', () => {
    expect(
      getCabinetHealth({
        entitlement,
        notifications,
        serviceState: undefined,
        usage,
        now: new Date('2026-04-24T00:00:00Z'),
      }),
    ).toBe('healthy');
  });

  it('escalates expired or nearly exhausted access', () => {
    expect(
      getCabinetHealth({
        entitlement: { ...entitlement, status: 'expired' },
        notifications,
        serviceState,
        usage,
      }),
    ).toBe('critical');

    expect(
      getCabinetHealth({
        entitlement,
        notifications,
        serviceState,
        usage: { ...usage, bandwidth_used_bytes: 98 },
      }),
    ).toBe('critical');
  });

  it('flags action-required notifications as attention', () => {
    expect(
      getCabinetHealth({
        entitlement,
        notifications: { ...notifications, action_required_notifications: 1 },
        serviceState,
        usage,
      }),
    ).toBe('attention');
  });

  it('prioritizes next-best-actions from backend state', () => {
    expect(
      getCabinetActionIds({
        entitlement: { ...entitlement, status: 'expired' },
        notifications,
        serviceState,
        trial: {
          days_remaining: 0,
          is_eligible: true,
          is_trial_active: false,
          trial_end: null,
          trial_start: null,
        },
        usage,
      }),
    ).toEqual(['startTrial', 'getConfig', 'secureAccount', 'inviteFriends']);

    expect(
      getCabinetActionIds({
        entitlement,
        notifications: { ...notifications, action_required_notifications: 1 },
        serviceState: { ...serviceState, device_credential: null },
        usage: { ...usage, bandwidth_used_bytes: 85 },
      }),
    ).toEqual([
      'finishProvisioning',
      'watchTraffic',
      'reviewNotifications',
      'getConfig',
    ]);
  });
});
