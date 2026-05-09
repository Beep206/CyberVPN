import { describe, expect, it } from 'vitest';

import {
  STAGE1_MANUAL_SUBSCRIPTION_AUDIT_ACTION,
  buildManualSubscriptionEndpoint,
  buildManualSubscriptionRequest,
  canApplyManualSubscription,
  summarizeManualSubscriptionResult,
  type ManualSubscriptionResult,
  type Stage1ManualSubscriptionRole,
} from '../customer-manual-subscription-model';

const allowedRoles: Stage1ManualSubscriptionRole[] = [
  'owner',
  'owner/super_admin',
  'owner_super_admin',
  'super_admin',
  'admin',
  'operator',
];

const deniedRoles: Stage1ManualSubscriptionRole[] = ['support', 'finance', 'viewer'];

describe('customer manual subscription model', () => {
  it('matches the backend subscription_create role gate', () => {
    for (const role of allowedRoles) {
      expect(canApplyManualSubscription(role)).toBe(true);
    }

    for (const role of deniedRoles) {
      expect(canApplyManualSubscription(role)).toBe(false);
    }
  });

  it('builds the backend endpoint and snake_case request payload', () => {
    expect(buildManualSubscriptionEndpoint('customer 1')).toBe(
      '/admin/mobile-users/customer%201/subscription/manual-grant',
    );

    expect(
      buildManualSubscriptionRequest({
        deviceLimit: 3,
        durationDays: 30,
        reason: '  payment provider failed; manual access approved  ',
        trafficLimitBytes: 2_147_483_648,
      }),
    ).toEqual({
      ok: true,
      payload: {
        device_limit: 3,
        duration_days: 30,
        reason: 'payment provider failed; manual access approved',
        traffic_limit_bytes: 2_147_483_648,
      },
    });
  });

  it('rejects invalid local input before calling the backend', () => {
    expect(
      buildManualSubscriptionRequest({
        deviceLimit: 1,
        durationDays: 30,
        reason: 'no',
        trafficLimitBytes: null,
      }),
    ).toMatchObject({ ok: false });

    expect(
      buildManualSubscriptionRequest({
        deviceLimit: 1,
        durationDays: 366,
        reason: 'manual access approved',
        trafficLimitBytes: null,
      }),
    ).toMatchObject({ ok: false });

    expect(
      buildManualSubscriptionRequest({
        deviceLimit: 11,
        durationDays: 30,
        reason: 'manual access approved',
        trafficLimitBytes: null,
      }),
    ).toMatchObject({ ok: false });

    expect(
      buildManualSubscriptionRequest({
        deviceLimit: 1,
        durationDays: 30,
        reason: 'manual access approved',
        trafficLimitBytes: 0,
      }),
    ).toMatchObject({ ok: false });
  });

  it('summarizes the safe response without raw VPN config fields', () => {
    const result: ManualSubscriptionResult & {
      short_uuid?: string;
      subscription_url?: string;
    } = {
      audit_action: STAGE1_MANUAL_SUBSCRIPTION_AUDIT_ACTION,
      config_delivery_required: true,
      created: false,
      duration_days: 30,
      expires_at: '2026-06-03T09:30:00Z',
      operation: 'extend',
      previous_expires_at: '2026-05-04T09:30:00Z',
      remnawave_uuid: '56b5f2d9-2c79-4826-a6fe-ccbbcfb3ca22',
      short_uuid: 'raw-short-secret',
      status: 'active',
      subscription_url: 'https://sub.example.local/raw-secret-token',
      subscription_url_changed: true,
      user_id: 'customer-1',
    };

    const summary = summarizeManualSubscriptionResult(result);
    const serialized = JSON.stringify(summary);

    expect(summary.auditAction).toBe(STAGE1_MANUAL_SUBSCRIPTION_AUDIT_ACTION);
    expect(summary.operation).toBe('extend');
    expect(serialized).not.toContain('raw-short-secret');
    expect(serialized).not.toContain('raw-secret-token');
    expect(serialized).not.toContain('https://');
  });
});
