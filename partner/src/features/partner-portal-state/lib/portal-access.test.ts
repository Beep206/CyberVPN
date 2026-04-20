import { describe, expect, it } from 'vitest';
import { createPartnerPortalScenarioState } from './portal-state';
import { countPartnerAccessibleSections, getPartnerRoleRouteAccess } from './portal-access';

describe('partner portal role access policy', () => {
  it('allows only owner/admin into team access', () => {
    const ownerState = createPartnerPortalScenarioState(
      'approved_probation',
      'creator_affiliate',
      'workspace_owner',
      'R2',
    );
    const analystState = createPartnerPortalScenarioState(
      'approved_probation',
      'creator_affiliate',
      'analyst',
      'R2',
    );

    expect(getPartnerRoleRouteAccess('team', ownerState)).toBe('admin');
    expect(getPartnerRoleRouteAccess('team', analystState)).toBe('none');
  });

  it('keeps finance hidden for traffic roles and integrations hidden for support roles', () => {
    const trafficState = createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'traffic_manager',
    );
    const supportState = createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'support_manager',
    );

    expect(getPartnerRoleRouteAccess('finance', trafficState)).toBe('none');
    expect(getPartnerRoleRouteAccess('integrations', supportState)).toBe('none');
  });

  it('counts accessible sections for an owner in active state', () => {
    const state = createPartnerPortalScenarioState(
      'active',
      'reseller_api',
      'workspace_owner',
    );

    expect(countPartnerAccessibleSections(state)).toBeGreaterThan(10);
  });

  it('keeps reseller route hidden outside reseller lane even for owner roles', () => {
    const state = createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'workspace_owner',
    );

    expect(getPartnerRoleRouteAccess('reseller', state)).toBe('none');
  });

  it('does not let roles bypass release-ring gating', () => {
    const ownerState = createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'workspace_owner',
      'R1',
    );

    expect(getPartnerRoleRouteAccess('conversions', ownerState)).toBe('none');
  });

  it('lets backend permission keys narrow route access below role defaults', () => {
    const ownerState = {
      ...createPartnerPortalScenarioState(
        'active',
        'creator_affiliate',
        'workspace_owner',
        'R4',
      ),
      currentPermissionKeys: ['workspace_read'],
    };

    expect(getPartnerRoleRouteAccess('codes', ownerState)).toBe('none');
    expect(getPartnerRoleRouteAccess('finance', ownerState)).toBe('none');
    expect(getPartnerRoleRouteAccess('dashboard', ownerState)).toBe('read');
  });
});
