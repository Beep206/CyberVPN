// @vitest-environment node

import { describe, expect, it } from 'vitest';
import type { components, paths } from '../generated/types';

const PHASE6_PARTNER_PATHS = [
  '/api/v1/pricebooks/resolve',
  '/api/v1/legal-documents/sets/resolve',
  '/api/v1/policy-acceptance/',
  '/api/v1/policy-acceptance/me',
  '/api/v1/partner-workspaces/me',
  '/api/v1/partner-workspaces/{workspace_id}',
  '/api/v1/partner-workspaces/{workspace_id}/codes',
  '/api/v1/partner-workspaces/{workspace_id}/statements',
  '/api/v1/partner-workspaces/{workspace_id}/conversion-records',
  '/api/v1/partner-workspaces/{workspace_id}/analytics-metrics',
  '/api/v1/partner-workspaces/{workspace_id}/report-exports',
  '/api/v1/partner-workspaces/{workspace_id}/review-requests',
  '/api/v1/partner-workspaces/{workspace_id}/traffic-declarations',
  '/api/v1/partner-workspaces/{workspace_id}/cases',
  '/api/v1/entitlements/current',
  '/api/v1/access-delivery-channels/current/service-state',
] as const satisfies readonly (keyof paths)[];

type Phase6PartnerWorkspaceResponse = components['schemas']['PartnerWorkspaceResponse'];
type Phase6PartnerStatementResponse = components['schemas']['PartnerStatementResponse'];
type Phase6PartnerWorkspaceTrafficDeclarationResponse =
  components['schemas']['PartnerWorkspaceTrafficDeclarationResponse'];
type Phase6CurrentEntitlementStateResponse = components['schemas']['CurrentEntitlementStateResponse'];
type Phase6CurrentServiceStateResponse = components['schemas']['CurrentServiceStateResponse'];

describe('Phase 6 generated API contract', () => {
  it('includes the frozen partner storefront and portal path families', () => {
    expect(PHASE6_PARTNER_PATHS).toContain('/api/v1/partner-workspaces/{workspace_id}/traffic-declarations');
    expect(PHASE6_PARTNER_PATHS).toContain('/api/v1/legal-documents/sets/resolve');
  });

  it('exposes the required partner-facing schemas', () => {
    const compileGuard: {
      workspace: Phase6PartnerWorkspaceResponse | null;
      statement: Phase6PartnerStatementResponse | null;
      trafficDeclaration: Phase6PartnerWorkspaceTrafficDeclarationResponse | null;
      currentEntitlementState: Phase6CurrentEntitlementStateResponse | null;
      currentServiceState: Phase6CurrentServiceStateResponse | null;
    } = {
      workspace: null,
      statement: null,
      trafficDeclaration: null,
      currentEntitlementState: null,
      currentServiceState: null,
    };

    expect(compileGuard).toEqual({
      workspace: null,
      statement: null,
      trafficDeclaration: null,
      currentEntitlementState: null,
      currentServiceState: null,
    });
  });
});
