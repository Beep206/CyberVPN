import { describe, expect, it } from 'vitest';
import {
  buildPartnerApplicationDraftPayload,
  canResubmitPartnerApplication,
  canWithdrawPartnerApplication,
  getPartnerApplicationWorkspaceStatus,
  isPartnerApplicationSubmittedStatus,
  mapApplicationDraftResponseToLocalDraft,
} from './application-contract';

describe('partner application contract helpers', () => {
  const response = {
    draft: {
      id: 'draft-1',
      partner_account_id: 'workspace-1',
      applicant_admin_user_id: 'user-1',
      workspace: {
        id: 'workspace-1',
        account_key: 'north-star-growth',
        display_name: 'North Star Growth',
        status: 'needs_info',
        current_role_key: 'owner',
        current_permission_keys: ['workspace_read', 'operations_write'],
      },
      draft_payload: {
        workspace_name: 'North Star Growth',
        contact_name: 'Alex Mercer',
        contact_email: 'ops@example.com',
        country: 'Germany',
        website: 'https://example.com',
        primary_lane: 'creator_affiliate',
        business_description: 'Growth studio',
        acquisition_channels: 'SEO',
        operating_regions: 'DACH',
        languages: 'en,de',
        support_contact: 'support@example.com',
        technical_contact: 'tech@example.com',
        finance_contact: 'finance@example.com',
        compliance_accepted: true,
      },
      review_ready: false,
      submitted_at: '2026-04-20T10:00:00Z',
      withdrawn_at: null,
      created_at: '2026-04-20T09:00:00Z',
      updated_at: '2026-04-20T10:15:00Z',
    },
    lane_applications: [],
    review_requests: [],
    attachments: [],
  } as const;

  it('maps backend draft responses to the local onboarding draft shape', () => {
    expect(
      mapApplicationDraftResponseToLocalDraft(response, 'fallback@example.com'),
    ).toEqual({
      workspaceName: 'North Star Growth',
      contactName: 'Alex Mercer',
      contactEmail: 'ops@example.com',
      country: 'Germany',
      website: 'https://example.com',
      primaryLane: 'creator_affiliate',
      businessDescription: 'Growth studio',
      acquisitionChannels: 'SEO',
      operatingRegions: 'DACH',
      languages: 'en,de',
      supportContact: 'support@example.com',
      technicalContact: 'tech@example.com',
      financeContact: 'finance@example.com',
      complianceAccepted: true,
      reviewReady: false,
      updatedAt: '2026-04-20T10:15:00Z',
    });
  });

  it('builds backend payloads from local drafts', () => {
    expect(
      buildPartnerApplicationDraftPayload({
        workspaceName: ' North Star Growth ',
        contactName: ' Alex Mercer ',
        contactEmail: ' ops@example.com ',
        country: ' Germany ',
        website: ' https://example.com ',
        primaryLane: 'creator_affiliate',
        businessDescription: ' Growth studio ',
        acquisitionChannels: ' SEO ',
        operatingRegions: ' DACH ',
        languages: ' en,de ',
        supportContact: ' support@example.com ',
        technicalContact: ' tech@example.com ',
        financeContact: ' finance@example.com ',
        complianceAccepted: true,
        reviewReady: true,
        updatedAt: null,
      }),
    ).toEqual({
      draft_payload: {
        workspace_name: 'North Star Growth',
        contact_name: 'Alex Mercer',
        contact_email: 'ops@example.com',
        country: 'Germany',
        website: 'https://example.com',
        primary_lane: 'creator_affiliate',
        business_description: 'Growth studio',
        acquisition_channels: 'SEO',
        operating_regions: 'DACH',
        languages: 'en,de',
        support_contact: 'support@example.com',
        technical_contact: 'tech@example.com',
        finance_contact: 'finance@example.com',
        compliance_accepted: true,
      },
      review_ready: true,
    });
  });

  it('derives application lifecycle helpers from workspace status', () => {
    expect(getPartnerApplicationWorkspaceStatus(response)).toBe('needs_info');
    expect(canResubmitPartnerApplication('needs_info')).toBe(true);
    expect(canWithdrawPartnerApplication('needs_info')).toBe(true);
    expect(isPartnerApplicationSubmittedStatus('needs_info')).toBe(false);
    expect(isPartnerApplicationSubmittedStatus('submitted')).toBe(true);
  });
});
