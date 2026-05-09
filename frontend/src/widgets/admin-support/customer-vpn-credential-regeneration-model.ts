export const STAGE1_CREDENTIAL_REGENERATION_AUDIT_ACTION =
  'customer_vpn_credentials_regenerated';

export type Stage1CredentialRegenerationRole =
  | 'admin'
  | 'operator'
  | 'owner'
  | 'owner/super_admin'
  | 'owner_super_admin'
  | 'super_admin'
  | 'support'
  | 'viewer';

export type CredentialRegenerationRequestPayload = {
  reason: string;
  revoke_only_passwords: boolean;
};

export type CredentialRegenerationResult = {
  audit_action: string;
  config_delivery_required: boolean;
  expires_at: string | null;
  regenerated_at: string;
  remnawave_uuid: string;
  revoke_only_passwords: boolean;
  short_uuid_changed: boolean;
  status: string;
  subscription_url_changed: boolean;
  user_id: string;
};

export type CredentialRegenerationRequestValidation =
  | {
      ok: true;
      payload: CredentialRegenerationRequestPayload;
    }
  | {
      error: string;
      ok: false;
    };

export type SafeCredentialRegenerationSummary = {
  auditAction: string;
  deliveryRequired: boolean;
  expiresAt: string | null;
  regeneratedAt: string;
  revokeOnlyPasswords: boolean;
  shortUuidChanged: boolean;
  status: string;
  subscriptionUrlChanged: boolean;
  userId: string;
  vpnIdentity: string;
};

const ALLOWED_CREDENTIAL_REGENERATION_ROLES = new Set<Stage1CredentialRegenerationRole>([
  'admin',
  'owner',
  'owner/super_admin',
  'owner_super_admin',
  'super_admin',
  'support',
]);

export function canRegenerateVpnCredentials(
  role: Stage1CredentialRegenerationRole,
): boolean {
  return ALLOWED_CREDENTIAL_REGENERATION_ROLES.has(role);
}

export function buildCredentialRegenerationEndpoint(userId: string): string {
  return `/admin/mobile-users/${encodeURIComponent(userId)}/vpn-user/regenerate-credentials`;
}

export function buildCredentialRegenerationRequest({
  reason,
  revokeOnlyPasswords,
}: {
  reason: string;
  revokeOnlyPasswords: boolean;
}): CredentialRegenerationRequestValidation {
  const trimmedReason = reason.trim();

  if (trimmedReason.length < 3) {
    return {
      error: 'Credential regeneration requires a support reason.',
      ok: false,
    };
  }

  if (trimmedReason.length > 1000) {
    return {
      error: 'Credential regeneration reason is too long.',
      ok: false,
    };
  }

  return {
    ok: true,
    payload: {
      reason: trimmedReason,
      revoke_only_passwords: revokeOnlyPasswords,
    },
  };
}

export function summarizeCredentialRegenerationResult(
  result: CredentialRegenerationResult,
): SafeCredentialRegenerationSummary {
  return {
    auditAction: result.audit_action,
    deliveryRequired: result.config_delivery_required,
    expiresAt: result.expires_at,
    regeneratedAt: result.regenerated_at,
    revokeOnlyPasswords: result.revoke_only_passwords,
    shortUuidChanged: result.short_uuid_changed,
    status: result.status,
    subscriptionUrlChanged: result.subscription_url_changed,
    userId: result.user_id,
    vpnIdentity: result.remnawave_uuid,
  };
}
