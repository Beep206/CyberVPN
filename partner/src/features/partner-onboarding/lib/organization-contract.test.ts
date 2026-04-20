import { describe, expect, it } from 'vitest';
import {
  buildOrganizationProfilePayload,
  mapOrganizationProfileToDraft,
} from './organization-contract';

describe('organization contract', () => {
  it('maps backend organization profile into partner application draft shape', () => {
    const draft = mapOrganizationProfileToDraft({
      partner_account_id: 'workspace-1',
      workspace_name: 'Northstar Media',
      website: 'https://northstar.example',
      country: 'DE',
      operating_regions: 'EU, LATAM',
      languages: 'de-DE, en-EN',
      primary_lane: 'creator_affiliate',
      contact_name: 'Alex',
      contact_email: 'alex@example.com',
      support_contact: 'support@example.com',
      technical_contact: 'tech@example.com',
      finance_contact: 'finance@example.com',
      business_description: 'Security-focused publishing studio',
      acquisition_channels: 'SEO, newsletter, Telegram',
      updated_at: '2026-04-20T10:00:00.000Z',
    });

    expect(draft.workspaceName).toBe('Northstar Media');
    expect(draft.primaryLane).toBe('creator_affiliate');
    expect(draft.technicalContact).toBe('tech@example.com');
  });

  it('builds backend payload from draft values', () => {
    const payload = buildOrganizationProfilePayload({
      workspaceName: 'Northstar Media',
      primaryLane: 'creator_affiliate',
      country: 'DE',
      website: 'https://northstar.example',
      contactName: 'Alex',
      contactEmail: 'alex@example.com',
      businessDescription: 'Security-focused publishing studio',
      acquisitionChannels: 'SEO, newsletter, Telegram',
      operatingRegions: 'EU, LATAM',
      languages: 'de-DE, en-EN',
      supportContact: 'support@example.com',
      technicalContact: 'tech@example.com',
      financeContact: 'finance@example.com',
      complianceAccepted: true,
      reviewReady: false,
      updatedAt: null,
    });

    expect(payload.workspace_name).toBe('Northstar Media');
    expect(payload.business_description).toContain('Security-focused');
    expect(payload.technical_contact).toBe('tech@example.com');
  });
});
