import { describe, expect, it } from 'vitest';
import {
  buildWorkspaceSettingsPayload,
  mapWorkspaceSettingsToDraft,
} from './workspace-settings-contract';

describe('workspace settings contract', () => {
  it('maps backend settings into foundation draft shape', () => {
    const draft = mapWorkspaceSettingsToDraft({
      partner_account_id: 'workspace-1',
      operator_email: 'owner@example.com',
      operator_display_name: 'Owner',
      operator_role: 'owner',
      is_email_verified: true,
      preferred_language: 'ru-RU',
      preferred_currency: 'EUR',
      workspace_security_alerts: true,
      payout_status_emails: true,
      product_announcements: false,
      require_mfa_for_workspace: true,
      prefer_passkeys: true,
      reviewed_active_sessions: false,
      updated_at: '2026-04-20T10:00:00.000Z',
    });

    expect(draft.preferredLanguage).toBe('ru-RU');
    expect(draft.requireMfaForWorkspace).toBe(true);
    expect(draft.preferPasskeys).toBe(true);
  });

  it('builds backend settings payload from draft', () => {
    const payload = buildWorkspaceSettingsPayload({
      preferredLanguage: 'en-EN',
      preferredCurrency: 'USD',
      workspaceSecurityAlerts: true,
      payoutStatusEmails: false,
      productAnnouncements: true,
      requireMfaForWorkspace: false,
      preferPasskeys: true,
      reviewedActiveSessions: true,
      updatedAt: null,
    });

    expect(payload.preferred_language).toBe('en-EN');
    expect(payload.payout_status_emails).toBe(false);
    expect(payload.reviewed_active_sessions).toBe(true);
  });
});
