export interface PartnerSettingsFoundationDraft {
  preferredLanguage: string;
  preferredCurrency: string;
  workspaceSecurityAlerts: boolean;
  payoutStatusEmails: boolean;
  productAnnouncements: boolean;
  requireMfaForWorkspace: boolean;
  preferPasskeys: boolean;
  reviewedActiveSessions: boolean;
  updatedAt: string | null;
}

export const PARTNER_SETTINGS_FOUNDATION_STORAGE_KEY =
  'ozoxy-partner-settings-foundation:v1';

export const EMPTY_PARTNER_SETTINGS_FOUNDATION_DRAFT: PartnerSettingsFoundationDraft = {
  preferredLanguage: '',
  preferredCurrency: 'USD',
  workspaceSecurityAlerts: true,
  payoutStatusEmails: true,
  productAnnouncements: false,
  requireMfaForWorkspace: false,
  preferPasskeys: false,
  reviewedActiveSessions: false,
  updatedAt: null,
};

function readStringField(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function readBooleanField(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

export function loadPartnerSettingsFoundationDraft(): PartnerSettingsFoundationDraft | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const rawDraft = window.localStorage.getItem(PARTNER_SETTINGS_FOUNDATION_STORAGE_KEY);
  if (!rawDraft) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawDraft) as Record<string, unknown>;

    return {
      preferredLanguage: readStringField(parsed.preferredLanguage),
      preferredCurrency: readStringField(parsed.preferredCurrency, 'USD'),
      workspaceSecurityAlerts: readBooleanField(parsed.workspaceSecurityAlerts, true),
      payoutStatusEmails: readBooleanField(parsed.payoutStatusEmails, true),
      productAnnouncements: readBooleanField(parsed.productAnnouncements),
      requireMfaForWorkspace: readBooleanField(parsed.requireMfaForWorkspace),
      preferPasskeys: readBooleanField(parsed.preferPasskeys),
      reviewedActiveSessions: readBooleanField(parsed.reviewedActiveSessions),
      updatedAt: parsed.updatedAt == null ? null : readStringField(parsed.updatedAt),
    };
  } catch {
    return null;
  }
}

export function savePartnerSettingsFoundationDraft(
  draft: PartnerSettingsFoundationDraft,
): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(
    PARTNER_SETTINGS_FOUNDATION_STORAGE_KEY,
    JSON.stringify(draft),
  );
}

export function clearPartnerSettingsFoundationDraft(): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.removeItem(PARTNER_SETTINGS_FOUNDATION_STORAGE_KEY);
}
