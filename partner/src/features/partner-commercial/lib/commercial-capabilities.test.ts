import { describe, expect, it } from 'vitest';
import { createPartnerPortalScenarioState } from '@/features/partner-portal-state/lib/portal-state';
import {
  getPartnerCampaignCapabilities,
  getPartnerCodeCapabilities,
  getPartnerCommercialSurfaceMode,
  getPartnerComplianceCapabilities,
} from './commercial-capabilities';

describe('partner commercial capabilities', () => {
  it('gives creator probation a starter codes surface', () => {
    const state = createPartnerPortalScenarioState(
      'approved_probation',
      'creator_affiliate',
      'traffic_manager',
    );

    expect(getPartnerCommercialSurfaceMode('codes', state)).toBe('starter');
    expect(getPartnerCodeCapabilities(state)).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'starter_code', availability: 'enabled' }),
      expect.objectContaining({ key: 'additional_codes', availability: 'conditional' }),
    ]));
  });

  it('keeps performance probation controlled and postback-ready in compliance', () => {
    const state = createPartnerPortalScenarioState(
      'approved_probation',
      'performance_media',
      'traffic_manager',
    );

    expect(getPartnerCommercialSurfaceMode('compliance', state)).toBe('controlled');
    expect(getPartnerComplianceCapabilities(state)).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'creative_approvals', availability: 'enabled' }),
      expect.objectContaining({ key: 'postback_readiness', availability: 'enabled' }),
    ]));
  });

  it('keeps reseller campaigns controlled even when the workspace is active', () => {
    const state = createPartnerPortalScenarioState(
      'active',
      'reseller_api',
      'workspace_owner',
    );

    expect(getPartnerCommercialSurfaceMode('campaigns', state)).toBe('controlled');
    expect(getPartnerCampaignCapabilities(state)).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'creative_library', availability: 'conditional' }),
      expect.objectContaining({ key: 'disclosure_templates', availability: 'enabled' }),
    ]));
  });

  it('downgrades codes to read-only when governance is limited', () => {
    const state = createPartnerPortalScenarioState(
      'restricted',
      'creator_affiliate',
      'workspace_owner',
    );

    expect(getPartnerCommercialSurfaceMode('codes', state)).toBe('read_only');
    expect(getPartnerCodeCapabilities(state).every((item) => item.availability === 'blocked')).toBe(true);
  });
});
