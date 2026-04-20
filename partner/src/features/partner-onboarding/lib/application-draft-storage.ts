export type PartnerPrimaryLane =
  | 'creator_affiliate'
  | 'performance_media'
  | 'reseller_api';

export interface PartnerApplicationDraft {
  workspaceName: string;
  contactName: string;
  contactEmail: string;
  country: string;
  website: string;
  primaryLane: PartnerPrimaryLane | '';
  businessDescription: string;
  acquisitionChannels: string;
  operatingRegions: string;
  languages: string;
  supportContact: string;
  technicalContact: string;
  financeContact: string;
  complianceAccepted: boolean;
  reviewReady: boolean;
  updatedAt: string | null;
}

export const PARTNER_APPLICATION_DRAFT_STORAGE_KEY =
  'ozoxy-partner-application-draft:v1';

export const EMPTY_PARTNER_APPLICATION_DRAFT: PartnerApplicationDraft = {
  workspaceName: '',
  contactName: '',
  contactEmail: '',
  country: '',
  website: '',
  primaryLane: '',
  businessDescription: '',
  acquisitionChannels: '',
  operatingRegions: '',
  languages: '',
  supportContact: '',
  technicalContact: '',
  financeContact: '',
  complianceAccepted: false,
  reviewReady: false,
  updatedAt: null,
};

function readStringField(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function readBooleanField(value: unknown): boolean {
  return value === true;
}

export function loadPartnerApplicationDraft(): PartnerApplicationDraft | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const rawDraft = window.localStorage.getItem(PARTNER_APPLICATION_DRAFT_STORAGE_KEY);
  if (!rawDraft) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawDraft) as Record<string, unknown>;

    return {
      workspaceName: readStringField(parsed.workspaceName),
      contactName: readStringField(parsed.contactName),
      contactEmail: readStringField(parsed.contactEmail),
      country: readStringField(parsed.country),
      website: readStringField(parsed.website),
      primaryLane: readStringField(parsed.primaryLane) as PartnerApplicationDraft['primaryLane'],
      businessDescription: readStringField(parsed.businessDescription),
      acquisitionChannels: readStringField(parsed.acquisitionChannels),
      operatingRegions: readStringField(parsed.operatingRegions),
      languages: readStringField(parsed.languages),
      supportContact: readStringField(parsed.supportContact),
      technicalContact: readStringField(parsed.technicalContact),
      financeContact: readStringField(parsed.financeContact),
      complianceAccepted: readBooleanField(parsed.complianceAccepted),
      reviewReady: readBooleanField(parsed.reviewReady),
      updatedAt: parsed.updatedAt == null ? null : readStringField(parsed.updatedAt),
    };
  } catch {
    return null;
  }
}

export function savePartnerApplicationDraft(draft: PartnerApplicationDraft): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(
    PARTNER_APPLICATION_DRAFT_STORAGE_KEY,
    JSON.stringify(draft),
  );
}

export function clearPartnerApplicationDraft(): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.removeItem(PARTNER_APPLICATION_DRAFT_STORAGE_KEY);
}
