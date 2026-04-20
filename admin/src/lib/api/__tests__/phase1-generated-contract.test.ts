// @vitest-environment node

import { describe, expect, it } from 'vitest';
import type { components, paths } from '../generated/types';

const PHASE1_ADMIN_PATHS = [
  '/api/v1/auth/login',
  '/api/v1/auth/me',
  '/api/v1/realms/',
  '/api/v1/realms/resolve',
  '/api/v1/admin/partner-workspaces',
  '/api/v1/admin/partner-workspaces/{workspace_id}',
  '/api/v1/partner-workspaces/me',
  '/api/v1/partner-workspaces/{workspace_id}',
  '/api/v1/partner-workspaces/{workspace_id}/members',
  '/api/v1/offers/admin',
  '/api/v1/pricebooks/admin',
  '/api/v1/program-eligibility/admin',
  '/api/v1/policies/',
  '/api/v1/legal-documents/',
  '/api/v1/policy-acceptance/',
  '/api/v1/security/risk-subjects',
  '/api/v1/security/risk-reviews',
  '/api/v1/security/eligibility/checks',
] as const satisfies readonly (keyof paths)[];

type Phase1WorkspaceResponse = components['schemas']['PartnerWorkspaceResponse'];
type Phase1RiskSubjectResponse = components['schemas']['RiskSubjectResponse'];
type Phase1PolicyVersionResponse = components['schemas']['PolicyVersionResponse'];

describe('Phase 1 generated API contract', () => {
  it('includes the frozen Phase 1 admin path families', () => {
    expect(PHASE1_ADMIN_PATHS).toContain('/api/v1/admin/partner-workspaces');
    expect(PHASE1_ADMIN_PATHS).toContain('/api/v1/security/risk-subjects');
  });

  it('exposes the required Phase 1 admin schemas', () => {
    const compileGuard: {
      workspace: Phase1WorkspaceResponse | null;
      riskSubject: Phase1RiskSubjectResponse | null;
      policyVersion: Phase1PolicyVersionResponse | null;
    } = {
      workspace: null,
      riskSubject: null,
      policyVersion: null,
    };

    expect(compileGuard).toEqual({
      workspace: null,
      riskSubject: null,
      policyVersion: null,
    });
  });
});
