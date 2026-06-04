import type {
  GetPartnerWorkspaceSettingsResponse,
  UpdatePartnerWorkspaceSettingsPayload,
} from '@/lib/api/partner-portal';
import type { UpdatePartnerWorkspacePasskeyPolicyRequest } from '@/lib/api/passkeys';
import type { PartnerSettingsFoundationDraft } from '@/features/partner-settings/lib/settings-foundation-storage';

export function mapWorkspaceSettingsToDraft(
  settings: GetPartnerWorkspaceSettingsResponse,
): PartnerSettingsFoundationDraft {
  return {
    preferredLanguage: settings.preferred_language,
    preferredCurrency: settings.preferred_currency,
    workspaceSecurityAlerts: settings.workspace_security_alerts,
    payoutStatusEmails: settings.payout_status_emails,
    productAnnouncements: settings.product_announcements,
    requireMfaForWorkspace: settings.require_mfa_for_workspace,
    preferPasskeys: settings.prefer_passkeys,
    reviewedActiveSessions: settings.reviewed_active_sessions,
    updatedAt: settings.updated_at ?? null,
  };
}

export function buildWorkspaceSettingsPayload(
  draft: PartnerSettingsFoundationDraft,
): UpdatePartnerWorkspaceSettingsPayload {
  return {
    preferred_language: draft.preferredLanguage,
    preferred_currency: draft.preferredCurrency,
    workspace_security_alerts: draft.workspaceSecurityAlerts,
    payout_status_emails: draft.payoutStatusEmails,
    product_announcements: draft.productAnnouncements,
    reviewed_active_sessions: draft.reviewedActiveSessions,
  };
}

export function buildWorkspacePasskeyPolicyPayload(
  draft: PartnerSettingsFoundationDraft,
): UpdatePartnerWorkspacePasskeyPolicyRequest {
  return {
    preferPasskeys: draft.preferPasskeys,
    requireMfaForWorkspace: draft.requireMfaForWorkspace,
  };
}

export function hasWorkspaceSettingsPayloadChanges(
  current: PartnerSettingsFoundationDraft,
  draft: PartnerSettingsFoundationDraft,
): boolean {
  return (
    current.preferredLanguage !== draft.preferredLanguage
    || current.preferredCurrency !== draft.preferredCurrency
    || current.workspaceSecurityAlerts !== draft.workspaceSecurityAlerts
    || current.payoutStatusEmails !== draft.payoutStatusEmails
    || current.productAnnouncements !== draft.productAnnouncements
    || current.reviewedActiveSessions !== draft.reviewedActiveSessions
  );
}

export function hasWorkspacePasskeyPolicyChanges(
  current: PartnerSettingsFoundationDraft,
  draft: PartnerSettingsFoundationDraft,
): boolean {
  return (
    current.requireMfaForWorkspace !== draft.requireMfaForWorkspace
    || current.preferPasskeys !== draft.preferPasskeys
  );
}
