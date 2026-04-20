import { describe, expect, it } from 'vitest';
import { createPartnerPortalScenarioState } from '@/features/partner-portal-state/lib/portal-state';
import {
  getPartnerConversionsCapabilities,
  getPartnerConversionsSurfaceMode,
  getPartnerIntegrationsCapabilities,
  getPartnerIntegrationsSurfaceMode,
  getPartnerResellerCapabilities,
  getPartnerResellerSurfaceMode,
} from './advanced-operational-capabilities';

describe('partner advanced operational capabilities', () => {
  it('keeps conversions lite on probation and dispute-aware when restricted', () => {
    const probationState = createPartnerPortalScenarioState(
      'approved_probation',
      'creator_affiliate',
      'analyst',
    );
    const restrictedState = createPartnerPortalScenarioState(
      'restricted',
      'performance_media',
      'support_manager',
    );

    expect(getPartnerConversionsSurfaceMode(probationState)).toBe('lite');
    expect(getPartnerConversionsSurfaceMode(restrictedState)).toBe('dispute');
    expect(getPartnerConversionsCapabilities(probationState)).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'customer_scope', availability: 'conditional' }),
      expect.objectContaining({ key: 'explainability', availability: 'enabled' }),
    ]));
  });

  it('keeps creator integrations selected and reseller integrations technical', () => {
    const creatorState = createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'technical_manager',
    );
    const resellerState = createPartnerPortalScenarioState(
      'active',
      'reseller_api',
      'technical_manager',
    );

    expect(getPartnerIntegrationsSurfaceMode(creatorState)).toBe('selected');
    expect(getPartnerIntegrationsSurfaceMode(resellerState)).toBe('technical');
    expect(getPartnerIntegrationsCapabilities(creatorState)).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'postback_credentials', availability: 'blocked' }),
    ]));
    expect(getPartnerIntegrationsCapabilities(resellerState)).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'storefront_api_keys', availability: 'enabled' }),
    ]));
  });

  it('keeps reseller console operational on active and constrained on restricted', () => {
    const activeState = createPartnerPortalScenarioState(
      'active',
      'reseller_api',
      'workspace_owner',
    );
    const restrictedState = createPartnerPortalScenarioState(
      'restricted',
      'reseller_api',
      'workspace_owner',
    );

    expect(getPartnerResellerSurfaceMode(activeState)).toBe('operational');
    expect(getPartnerResellerSurfaceMode(restrictedState)).toBe('constrained');
    expect(getPartnerResellerCapabilities(restrictedState)).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'linked_domains', availability: 'conditional' }),
    ]));
  });
});
