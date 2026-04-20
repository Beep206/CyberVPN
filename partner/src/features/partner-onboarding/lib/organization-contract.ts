import type {
  GetPartnerWorkspaceOrganizationProfileResponse,
  UpdatePartnerWorkspaceOrganizationProfilePayload,
} from '@/lib/api/partner-portal';
import type { PartnerApplicationDraft } from '@/features/partner-onboarding/lib/application-draft-storage';

export function mapOrganizationProfileToDraft(
  profile: GetPartnerWorkspaceOrganizationProfileResponse,
): PartnerApplicationDraft {
  return {
    workspaceName: profile.workspace_name,
    primaryLane: (profile.primary_lane as PartnerApplicationDraft['primaryLane']) || '',
    country: profile.country,
    website: profile.website,
    contactName: profile.contact_name,
    contactEmail: profile.contact_email,
    businessDescription: profile.business_description,
    acquisitionChannels: profile.acquisition_channels,
    operatingRegions: profile.operating_regions,
    languages: profile.languages,
    supportContact: profile.support_contact,
    technicalContact: profile.technical_contact,
    financeContact: profile.finance_contact,
    complianceAccepted: false,
    reviewReady: false,
    updatedAt: profile.updated_at ?? null,
  };
}

export function buildOrganizationProfilePayload(
  draft: PartnerApplicationDraft,
): UpdatePartnerWorkspaceOrganizationProfilePayload {
  return {
    workspace_name: draft.workspaceName,
    website: draft.website,
    country: draft.country,
    operating_regions: draft.operatingRegions,
    languages: draft.languages,
    contact_name: draft.contactName,
    contact_email: draft.contactEmail,
    support_contact: draft.supportContact,
    technical_contact: draft.technicalContact,
    finance_contact: draft.financeContact,
    business_description: draft.businessDescription,
    acquisition_channels: draft.acquisitionChannels,
  };
}
