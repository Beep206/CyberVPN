import { beforeEach, describe, expect, it } from 'vitest';
import {
  PARTNER_PORTAL_STATE_STORAGE_KEY,
  clearPartnerPortalState,
  createPartnerPortalScenarioState,
  derivePartnerReleaseRing,
  derivePartnerPortalScenario,
  loadPartnerPortalState,
  savePartnerPortalState,
} from './portal-state';

describe('partner portal state storage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('saves and loads the scenario state', () => {
    const state = createPartnerPortalScenarioState(
      'approved_probation',
      'reseller_api',
      'technical_manager',
    );

    savePartnerPortalState(state);

    expect(loadPartnerPortalState()).toEqual(state);
  });

  it('builds workspace, commercial, reporting, finance, and PP6 operational state', () => {
    const state = createPartnerPortalScenarioState(
      'active',
      'reseller_api',
      'workspace_owner',
    );

    expect(state.teamMembers.some((member) => member.role === 'workspace_owner')).toBe(true);
    expect(state.laneMemberships.find((lane) => lane.lane === 'reseller_api')?.status).toBe('approved_active');
    expect(state.legalDocuments.some((document) => document.kind === 'reseller_annex')).toBe(true);
    expect(state.codes.length).toBeGreaterThan(0);
    expect(state.campaignAssets.length).toBeGreaterThan(0);
    expect(state.complianceTasks.some((task) => task.kind === 'support_ownership')).toBe(true);
    expect(state.analyticsMetrics.length).toBeGreaterThan(0);
    expect(state.reportExports.some((item) => item.kind === 'statement_export')).toBe(true);
    expect(state.financeStatements.some((statement) => statement.status === 'ready')).toBe(true);
    expect(state.payoutAccounts.some((account) => account.status === 'ready')).toBe(true);
    expect(state.financeSnapshot.availableEarnings).not.toBe('$0');
    expect(state.conversionRecords.length).toBeGreaterThan(0);
    expect(state.integrationCredentials.length).toBeGreaterThan(0);
    expect(state.integrationDeliveryLogs.length).toBeGreaterThan(0);
    expect(state.resellerStorefronts.length).toBeGreaterThan(0);
    expect(state.resellerSnapshot.pricebookLabel).not.toBe('');
    expect(state.releaseRing).toBe('R4');
  });

  it('keeps dispute and blocked finance posture visible in restricted state', () => {
    const state = createPartnerPortalScenarioState(
      'restricted',
      'performance_media',
      'finance_manager',
    );

    expect(state.financeReadiness).toBe('blocked');
    expect(state.cases.some((item) => item.kind === 'payout_dispute')).toBe(true);
    expect(state.cases.some((item) => item.kind === 'attribution_dispute')).toBe(true);
    expect(state.financeStatements.some((statement) => statement.status === 'blocked')).toBe(true);
    expect(state.payoutAccounts.some((account) => account.status === 'blocked')).toBe(true);
  });

  it('derives a review scenario when the application draft is marked ready', () => {
    expect(derivePartnerPortalScenario({
      workspaceName: 'North Star',
      contactName: 'Alex',
      contactEmail: 'ops@example.com',
      country: 'DE',
      website: 'https://example.com',
      primaryLane: 'creator_affiliate',
      businessDescription: 'Traffic team',
      acquisitionChannels: 'SEO',
      operatingRegions: '',
      languages: '',
      supportContact: '',
      technicalContact: '',
      financeContact: '',
      complianceAccepted: true,
      reviewReady: true,
      updatedAt: '2026-04-18T12:00:00.000Z',
    })).toBe('needs_info');
  });

  it('derives rollout rings from the lane and lifecycle state', () => {
    expect(derivePartnerReleaseRing('draft')).toBe('R1');
    expect(derivePartnerReleaseRing('approved_probation', 'performance_media')).toBe('R1');
    expect(derivePartnerReleaseRing('active', 'creator_affiliate')).toBe('R2');
    expect(derivePartnerReleaseRing('active', 'performance_media')).toBe('R3');
    expect(derivePartnerReleaseRing('restricted', 'reseller_api')).toBe('R4');
  });

  it('hydrates a legacy stored state by deriving a release ring when the field is missing', () => {
    const state = createPartnerPortalScenarioState(
      'active',
      'performance_media',
      'technical_manager',
    );
    const legacyState = { ...state };

    delete legacyState.releaseRing;

    window.localStorage.setItem(
      PARTNER_PORTAL_STATE_STORAGE_KEY,
      JSON.stringify(legacyState),
    );

    expect(loadPartnerPortalState()?.releaseRing).toBe('R3');
  });

  it('clears the stored state', () => {
    savePartnerPortalState(createPartnerPortalScenarioState('draft'));

    clearPartnerPortalState();

    expect(window.localStorage.getItem(PARTNER_PORTAL_STATE_STORAGE_KEY)).toBeNull();
  });
});
