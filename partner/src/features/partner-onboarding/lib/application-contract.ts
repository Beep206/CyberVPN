import type {
  CreatePartnerApplicationDraftPayload,
  GetCurrentPartnerApplicationDraftResponse,
  UpdatePartnerApplicationDraftPayload,
} from '@/lib/api/partner-portal';
import type {
  PartnerApplicationDraft,
  PartnerPrimaryLane,
} from '@/features/partner-onboarding/lib/application-draft-storage';

export type PartnerApplicationWorkspaceStatus =
  | 'draft'
  | 'email_verified'
  | 'submitted'
  | 'under_review'
  | 'needs_info'
  | 'waitlisted'
  | 'approved_probation'
  | 'active'
  | 'restricted'
  | 'suspended'
  | 'rejected'
  | 'terminated';

export function mapApplicationDraftResponseToLocalDraft(
  response: GetCurrentPartnerApplicationDraftResponse,
  fallbackEmail?: string | null,
): PartnerApplicationDraft {
  const payload = response.draft.draft_payload;
  return {
    workspaceName: payload.workspace_name ?? '',
    contactName: payload.contact_name ?? '',
    contactEmail: payload.contact_email || fallbackEmail || '',
    country: payload.country ?? '',
    website: payload.website ?? '',
    primaryLane: (payload.primary_lane || '') as PartnerPrimaryLane | '',
    businessDescription: payload.business_description ?? '',
    acquisitionChannels: payload.acquisition_channels ?? '',
    operatingRegions: payload.operating_regions ?? '',
    languages: payload.languages ?? '',
    supportContact: payload.support_contact ?? '',
    technicalContact: payload.technical_contact ?? '',
    financeContact: payload.finance_contact ?? '',
    complianceAccepted: payload.compliance_accepted === true,
    reviewReady: response.draft.review_ready,
    updatedAt: response.draft.updated_at ?? null,
  };
}

export function buildPartnerApplicationDraftPayload(
  draft: PartnerApplicationDraft,
): CreatePartnerApplicationDraftPayload & UpdatePartnerApplicationDraftPayload {
  return {
    draft_payload: {
      workspace_name: draft.workspaceName.trim(),
      contact_name: draft.contactName.trim(),
      contact_email: draft.contactEmail.trim(),
      country: draft.country.trim(),
      website: draft.website.trim(),
      primary_lane: draft.primaryLane,
      business_description: draft.businessDescription.trim(),
      acquisition_channels: draft.acquisitionChannels.trim(),
      operating_regions: draft.operatingRegions.trim(),
      languages: draft.languages.trim(),
      support_contact: draft.supportContact.trim(),
      technical_contact: draft.technicalContact.trim(),
      finance_contact: draft.financeContact.trim(),
      compliance_accepted: draft.complianceAccepted,
    },
    review_ready: draft.reviewReady,
  };
}

export function getPartnerApplicationWorkspaceStatus(
  response: GetCurrentPartnerApplicationDraftResponse | null | undefined,
): PartnerApplicationWorkspaceStatus | null {
  return (response?.draft.workspace.status as PartnerApplicationWorkspaceStatus | undefined) ?? null;
}

export function isPartnerApplicationSubmittedStatus(
  status: PartnerApplicationWorkspaceStatus | null | undefined,
): boolean {
  return Boolean(
    status
    && [
      'submitted',
      'under_review',
      'waitlisted',
      'approved_probation',
      'active',
      'restricted',
      'suspended',
    ].includes(status),
  );
}

export function canWithdrawPartnerApplication(
  status: PartnerApplicationWorkspaceStatus | null | undefined,
): boolean {
  return Boolean(
    status
    && [
      'draft',
      'email_verified',
      'submitted',
      'under_review',
      'needs_info',
      'waitlisted',
    ].includes(status),
  );
}

export function canResubmitPartnerApplication(
  status: PartnerApplicationWorkspaceStatus | null | undefined,
): boolean {
  return status === 'needs_info' || status === 'waitlisted';
}
