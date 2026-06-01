import { describe, expect, it } from 'vitest';
import {
  doesPartnerNavGroupNeedAttention,
  getPartnerNavGroups,
  getPartnerNavPresentation,
} from '@/features/partner-shell/lib/partner-nav-presentation';
import { createPartnerPortalScenarioState } from '@/features/partner-portal-state/lib/portal-state';

describe('partner nav presentation', () => {
  it('groups the full active reseller inventory by approved IA order', () => {
    const state = createPartnerPortalScenarioState(
      'active',
      'reseller_api',
      'workspace_owner',
      'R4',
    );

    const groups = getPartnerNavGroups(state);

    expect(groups.map((group) => group.id)).toEqual([
      'main',
      'onboarding',
      'workspace',
      'promotion',
      'results',
      'finance',
      'control',
      'technical',
    ]);
    expect(groups[0].items.map(({ item }) => item.href)).toEqual([
      '/dashboard',
      '/notifications',
    ]);
    expect(groups.at(-1)?.items.map(({ item }) => item.href)).toEqual([
      '/integrations',
      '/reseller',
    ]);
  });

  it('keeps release-ring and reseller-ineligible routes out of grouped nav', () => {
    const state = createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'workspace_owner',
      'R1',
    );

    const groups = getPartnerNavGroups(state);
    const hrefs = groups.flatMap((group) => group.items.map(({ item }) => item.href));

    expect(hrefs).not.toContain('/conversions');
    expect(hrefs).not.toContain('/integrations');
    expect(hrefs).not.toContain('/reseller');
    expect(groups.map((group) => group.id)).not.toContain('technical');
  });

  it('maps lifecycle visibility to task, limited, and read-only badges', () => {
    const draftState = createPartnerPortalScenarioState(
      'draft',
      'creator_affiliate',
      'workspace_owner',
      'R4',
    );
    const probationState = createPartnerPortalScenarioState(
      'approved_probation',
      'creator_affiliate',
      'workspace_owner',
      'R4',
    );
    const analystState = createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'analyst',
      'R4',
    );

    expect(getPartnerNavPresentation('cases', draftState)).toMatchObject({
      state: 'task',
      badgeKey: 'badgeTask',
    });
    expect(getPartnerNavPresentation('codes', probationState)).toMatchObject({
      state: 'limited',
      badgeKey: 'badgeLimited',
    });
    expect(getPartnerNavPresentation('finance', analystState)).toMatchObject({
      state: 'readOnly',
      badgeKey: 'badgeReadOnly',
    });
  });

  it('marks groups with task or limited routes as needing attention', () => {
    const state = createPartnerPortalScenarioState(
      'draft',
      'creator_affiliate',
      'workspace_owner',
      'R4',
    );

    const groups = getPartnerNavGroups(state);
    const controlGroup = groups.find((group) => group.id === 'control');

    expect(controlGroup).toBeDefined();
    expect(controlGroup ? doesPartnerNavGroupNeedAttention(controlGroup) : false).toBe(true);
  });
});
