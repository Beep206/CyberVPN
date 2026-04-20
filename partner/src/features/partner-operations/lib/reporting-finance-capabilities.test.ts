import { describe, expect, it } from 'vitest';
import { createPartnerPortalScenarioState } from '@/features/partner-portal-state/lib/portal-state';
import {
  getPartnerAnalyticsCapabilities,
  getPartnerAnalyticsSurfaceMode,
  getPartnerCasesCapabilities,
  getPartnerCasesSurfaceMode,
  getPartnerFinanceCapabilities,
  getPartnerFinanceSurfaceMode,
} from './reporting-finance-capabilities';

describe('partner reporting, finance, and cases capabilities', () => {
  it('keeps analytics lite on probation', () => {
    const state = createPartnerPortalScenarioState(
      'approved_probation',
      'creator_affiliate',
      'analyst',
    );

    expect(getPartnerAnalyticsSurfaceMode(state)).toBe('lite');
    expect(getPartnerAnalyticsCapabilities(state)).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'overview_dashboards', availability: 'enabled' }),
      expect.objectContaining({ key: 'statement_exports', availability: 'blocked' }),
    ]));
  });

  it('keeps finance onboarding on probation and blocked under restriction', () => {
    const probationState = createPartnerPortalScenarioState(
      'approved_probation',
      'performance_media',
      'finance_manager',
    );
    const restrictedState = createPartnerPortalScenarioState(
      'restricted',
      'performance_media',
      'finance_manager',
    );

    expect(getPartnerFinanceSurfaceMode(probationState)).toBe('onboarding');
    expect(getPartnerFinanceCapabilities(probationState)).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'payout_accounts', availability: 'enabled' }),
      expect.objectContaining({ key: 'payout_actions', availability: 'blocked' }),
    ]));
    expect(getPartnerFinanceSurfaceMode(restrictedState)).toBe('blocked');
  });

  it('upgrades cases from applicant to operational and dispute modes', () => {
    const reviewState = createPartnerPortalScenarioState(
      'needs_info',
      'creator_affiliate',
      'support_manager',
    );
    const activeState = createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'support_manager',
    );
    const restrictedState = createPartnerPortalScenarioState(
      'restricted',
      'creator_affiliate',
      'support_manager',
    );

    expect(getPartnerCasesSurfaceMode(reviewState)).toBe('applicant');
    expect(getPartnerCasesSurfaceMode(activeState)).toBe('operational');
    expect(getPartnerCasesSurfaceMode(restrictedState)).toBe('dispute');
    expect(getPartnerCasesCapabilities(restrictedState)).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'payout_disputes', availability: 'enabled' }),
    ]));
  });
});
