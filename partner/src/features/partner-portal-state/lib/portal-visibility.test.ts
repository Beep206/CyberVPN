import { describe, expect, it } from 'vitest';
import { createPartnerPortalScenarioState } from './portal-state';
import {
  getPartnerRouteBlockReason,
  getPartnerRouteVisibility,
  getPartnerVisibilityBand,
} from './portal-visibility';

describe('partner portal visibility policy', () => {
  it('keeps codes hidden for draft applicants', () => {
    const state = createPartnerPortalScenarioState('draft', 'creator_affiliate');

    expect(getPartnerVisibilityBand(state.workspaceStatus)).toBe('pre_submit');
    expect(getPartnerRouteVisibility('codes', state)).toBe('hidden');
    expect(getPartnerRouteVisibility('cases', state)).toBe('task');
  });

  it('opens finance as task-driven during probation', () => {
    const state = createPartnerPortalScenarioState(
      'approved_probation',
      'creator_affiliate',
    );

    expect(getPartnerRouteVisibility('finance', state)).toBe('task');
    expect(getPartnerRouteVisibility('analytics', state)).toBe('limited');
  });

  it('downgrades restricted finance to read-only and keeps reseller hidden when not applicable', () => {
    const state = createPartnerPortalScenarioState(
      'restricted',
      'creator_affiliate',
    );

    expect(getPartnerRouteVisibility('finance', state)).toBe('read');
    expect(getPartnerRouteVisibility('reseller', state)).toBe('hidden');
  });

  it('keeps analytics readable for terminal workspace history', () => {
    const state = {
      ...createPartnerPortalScenarioState('restricted', 'creator_affiliate'),
      workspaceStatus: 'terminated' as const,
    };

    expect(getPartnerVisibilityBand(state.workspaceStatus)).toBe('terminal');
    expect(getPartnerRouteVisibility('analytics', state)).toBe('read');
  });

  it('keeps conversions hidden until the creator launch ring opens', () => {
    const state = createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'workspace_owner',
      'R1',
    );

    expect(getPartnerRouteBlockReason('conversions', state)).toBe('release_ring');
    expect(getPartnerRouteVisibility('conversions', state)).toBe('hidden');
  });

  it('keeps integrations behind the performance rollout ring', () => {
    const state = createPartnerPortalScenarioState(
      'active',
      'performance_media',
      'technical_manager',
      'R2',
    );

    expect(getPartnerRouteBlockReason('integrations', state)).toBe('release_ring');
    expect(getPartnerRouteVisibility('integrations', state)).toBe('hidden');
  });

  it('opens reseller console only when both lane posture and rollout ring are ready', () => {
    const state = createPartnerPortalScenarioState(
      'active',
      'reseller_api',
      'workspace_owner',
      'R4',
    );

    expect(getPartnerRouteBlockReason('reseller', state)).toBeNull();
    expect(getPartnerRouteVisibility('reseller', state)).toBe('full');
  });
});
