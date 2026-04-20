import type {
  GetPartnerWorkspaceSettingsResponse,
  UpdatePartnerWorkspaceSettingsPayload,
} from '@/lib/api/partner-portal';
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
    require_mfa_for_workspace: draft.requireMfaForWorkspace,
    prefer_passkeys: draft.preferPasskeys,
    reviewed_active_sessions: draft.reviewedActiveSessions,
  };
}
