import { describe, expect, it } from 'vitest';

import {
  STAGE1_CREDENTIAL_REGENERATION_AUDIT_ACTION,
  buildCredentialRegenerationEndpoint,
  buildCredentialRegenerationRequest,
  canRegenerateVpnCredentials,
  summarizeCredentialRegenerationResult,
  type CredentialRegenerationResult,
  type Stage1CredentialRegenerationRole,
} from '../customer-vpn-credential-regeneration-model';

const allowedRoles: Stage1CredentialRegenerationRole[] = [
  'owner',
  'owner/super_admin',
  'owner_super_admin',
  'super_admin',
  'admin',
  'support',
];

const deniedRoles: Stage1CredentialRegenerationRole[] = ['operator', 'viewer'];

describe('customer VPN credential regeneration model', () => {
  it('matches the backend role gate for S1-VPN-008', () => {
    for (const role of allowedRoles) {
      expect(canRegenerateVpnCredentials(role)).toBe(true);
    }

    for (const role of deniedRoles) {
      expect(canRegenerateVpnCredentials(role)).toBe(false);
    }
  });

  it('builds the backend endpoint and snake_case request payload', () => {
    expect(buildCredentialRegenerationEndpoint('customer 1')).toBe(
      '/admin/mobile-users/customer%201/vpn-user/regenerate-credentials',
    );

    expect(
      buildCredentialRegenerationRequest({
        reason: '  support confirmed lost device  ',
        revokeOnlyPasswords: true,
      }),
    ).toEqual({
      ok: true,
      payload: {
        reason: 'support confirmed lost device',
        revoke_only_passwords: true,
      },
    });
  });

  it('rejects invalid support reasons before calling the backend', () => {
    expect(
      buildCredentialRegenerationRequest({
        reason: 'no',
        revokeOnlyPasswords: false,
      }),
    ).toMatchObject({ ok: false });

    expect(
      buildCredentialRegenerationRequest({
        reason: 'x'.repeat(1001),
        revokeOnlyPasswords: false,
      }),
    ).toMatchObject({ ok: false });
  });

  it('summarizes the safe response without raw VPN secrets', () => {
    const result: CredentialRegenerationResult & {
      short_uuid?: string;
      subscription_url?: string;
    } = {
      audit_action: STAGE1_CREDENTIAL_REGENERATION_AUDIT_ACTION,
      config_delivery_required: true,
      expires_at: '2026-06-03T09:30:00Z',
      regenerated_at: '2026-05-04T09:30:00Z',
      remnawave_uuid: '56b5f2d9-2c79-4826-a6fe-ccbbcfb3ca22',
      revoke_only_passwords: false,
      short_uuid: 'raw-short-secret',
      short_uuid_changed: true,
      status: 'ACTIVE',
      subscription_url: 'https://sub.example.local/raw-secret-token',
      subscription_url_changed: true,
      user_id: 'customer-1',
    };

    const summary = summarizeCredentialRegenerationResult(result);
    const serialized = JSON.stringify(summary);

    expect(summary.auditAction).toBe(STAGE1_CREDENTIAL_REGENERATION_AUDIT_ACTION);
    expect(serialized).not.toContain('raw-short-secret');
    expect(serialized).not.toContain('raw-secret-token');
    expect(serialized).not.toContain('https://');
  });
});
