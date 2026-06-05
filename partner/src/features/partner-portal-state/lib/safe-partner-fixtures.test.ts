import { describe, expect, it } from 'vitest';
import { getPartnerRoleRouteAccess } from './portal-access';
import { createPartnerPortalScenarioState } from './portal-state';
import { getPartnerVisibilityBand } from './portal-visibility';
import { buildPartnerPortalRuntimeState } from './runtime-state';
import {
  SAFE_PARTNER_ROLE_PERMISSION_FIXTURES,
  createSafePartnerBusinessFlowFixture,
  createSafePartnerDisabledWorkspaceFixture,
  createSafePartnerSuspendedWorkspaceFixture,
} from './safe-partner-fixtures';

describe('safe partner fixture pack', () => {
  it('maps partner codes, attributed customers, earnings, and payout history into runtime state', () => {
    const fixture = createSafePartnerBusinessFlowFixture();
    const state = buildPartnerPortalRuntimeState({
      baseState: createPartnerPortalScenarioState(
        'active',
        'performance_media',
        'workspace_owner',
        'R4',
      ),
      workspace: fixture.workspace,
      workspaceAnalyticsMetrics: fixture.workspaceAnalyticsMetrics,
      workspaceCases: fixture.workspaceCases,
      workspaceCodes: fixture.workspaceCodes,
      workspaceConversionRecords: fixture.workspaceConversionRecords,
      workspaceNotifications: fixture.workspaceNotifications,
      workspacePayoutAccounts: fixture.workspacePayoutAccounts,
      workspaceReportExports: fixture.workspaceReportExports,
      workspaceReviewRequests: fixture.workspaceReviewRequests,
      workspaceStatements: fixture.workspaceStatements,
      workspaceTrafficDeclarations: fixture.workspaceTrafficDeclarations,
    });

    expect(state.workspaceDataSource).toBe('canonical');
    expect(state.codes).toEqual(expect.arrayContaining([
      expect.objectContaining({
        label: 'CYBA-SAFE-42',
        notes: ['Markup 12.50%'],
        status: 'active',
      }),
      expect.objectContaining({
        label: 'CYBA-PAUSED-07',
        notes: ['Markup 0.00%'],
        status: 'paused',
      }),
    ]));
    expect(state.conversionRecords).toEqual(expect.arrayContaining([
      expect.objectContaining({
        codeLabel: 'CYBA-SAFE-42',
        customerLabel: 'masked-customer-001',
        status: 'commissionable',
      }),
      expect.objectContaining({
        codeLabel: 'CYBA-PAUSED-07',
        customerLabel: 'masked-customer-003',
        status: 'reversed',
      }),
    ]));
    expect(state.financeSnapshot).toMatchObject({
      availableEarnings: '$280.00',
      currency: 'USD',
      nextPayoutForecast: '$280.00',
      onHoldEarnings: '$195.00',
      reserves: '$20.00',
    });
    expect(state.payoutAccounts).toEqual(expect.arrayContaining([
      expect.objectContaining({ label: 'Safe fixture settlement account', status: 'ready' }),
      expect.objectContaining({ label: 'Secondary review wallet', status: 'pending_review' }),
    ]));
    expect(fixture.workspacePayoutHistory.map((item) => item.instruction_status)).toEqual([
      'draft',
      'approved',
      'rejected',
    ]);
    expect(fixture.workspacePayoutHistory.every((item) => (
      item.notes.some((note) => note.toLowerCase().includes('safe fixture'))
    ))).toBe(true);
  });

  it('keeps partner role boundaries explicit in the safe fixture pack', () => {
    const baseState = createPartnerPortalScenarioState(
      'active',
      'performance_media',
      'workspace_owner',
      'R4',
    );

    const financeState = {
      ...baseState,
      currentPermissionKeys: SAFE_PARTNER_ROLE_PERMISSION_FIXTURES.finance,
      workspaceRole: 'finance_manager' as const,
    };
    const analystState = {
      ...baseState,
      currentPermissionKeys: SAFE_PARTNER_ROLE_PERMISSION_FIXTURES.analyst,
      workspaceRole: 'analyst' as const,
    };
    const trafficState = {
      ...baseState,
      currentPermissionKeys: SAFE_PARTNER_ROLE_PERMISSION_FIXTURES.traffic,
      workspaceRole: 'traffic_manager' as const,
    };

    expect(getPartnerRoleRouteAccess('finance', financeState)).toBe('write');
    expect(getPartnerRoleRouteAccess('finance', analystState)).toBe('read');
    expect(getPartnerRoleRouteAccess('finance', trafficState)).toBe('none');
    expect(getPartnerRoleRouteAccess('team', analystState)).toBe('none');
  });

  it('constrains suspended workspaces to readable partner history without active codes', () => {
    const fixture = createSafePartnerSuspendedWorkspaceFixture();
    const state = buildPartnerPortalRuntimeState({
      baseState: createPartnerPortalScenarioState(
        'active',
        'performance_media',
        'workspace_owner',
        'R4',
      ),
      workspace: fixture.workspace,
      workspaceCodes: fixture.workspaceCodes,
      workspacePayoutAccounts: fixture.workspacePayoutAccounts,
      workspaceStatements: fixture.workspaceStatements,
    });

    expect(state.workspaceStatus).toBe('suspended');
    expect(getPartnerVisibilityBand(state.workspaceStatus)).toBe('constrained');
    expect(state.codes.every((code) => code.status === 'paused')).toBe(true);
    expect(state.payoutAccounts[0]).toEqual(expect.objectContaining({
      status: 'blocked',
      notes: expect.arrayContaining(['Suspended: safe_fixture_policy_hold.']),
    }));
    expect(getPartnerRoleRouteAccess('codes', state)).toBe('read');
    expect(getPartnerRoleRouteAccess('finance', state)).toBe('read');
  });

  it('treats disabled terminal workspaces as workspace-read-only history', () => {
    const fixture = createSafePartnerDisabledWorkspaceFixture();
    const state = buildPartnerPortalRuntimeState({
      baseState: createPartnerPortalScenarioState(
        'restricted',
        'performance_media',
        'analyst',
        'R4',
      ),
      workspace: fixture.workspace,
      workspaceCodes: fixture.workspaceCodes,
      workspaceConversionRecords: fixture.workspaceConversionRecords,
      workspacePayoutAccounts: fixture.workspacePayoutAccounts,
      workspaceStatements: fixture.workspaceStatements,
    });

    expect(state.workspaceStatus).toBe('terminated');
    expect(getPartnerVisibilityBand(state.workspaceStatus)).toBe('terminal');
    expect(state.currentPermissionKeys).toEqual(['workspace_read']);
    expect(state.codes).toEqual([]);
    expect(state.conversionRecords).toEqual([]);
    expect(state.payoutAccounts).toEqual([]);
    expect(state.financeSnapshot.availableEarnings).toBe('$0.00');
    expect(getPartnerRoleRouteAccess('dashboard', state)).toBe('read');
    expect(getPartnerRoleRouteAccess('codes', state)).toBe('none');
    expect(getPartnerRoleRouteAccess('finance', state)).toBe('none');
  });
});
