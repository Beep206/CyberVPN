import { describe, expect, it } from 'vitest';
import {
  deriveCanonicalComplianceTasks,
  getCasesRestrictionReasons,
  getComplianceRestrictionReasons,
} from './compliance-runtime';

describe('compliance runtime helpers', () => {
  it('derives canonical compliance tasks from declarations, review requests, and blocked reasons', () => {
    const tasks = deriveCanonicalComplianceTasks({
      complianceReadiness: 'evidence_requested',
      governanceState: 'warning',
      primaryLane: 'performance_media',
      reviewRequests: [
        {
          id: 'request_001',
          kind: 'support_ownership',
          dueDate: '2026-04-22T10:00:00Z',
          status: 'submitted',
          availableActions: ['submit_response'],
          threadEvents: [],
        },
      ],
      trafficDeclarations: [
        {
          id: 'decl_001',
          kind: 'approved_sources',
          status: 'complete',
          scopeLabel: 'Owned domains',
          updatedAt: '2026-04-20T10:00:00Z',
          notes: ['Domains are declared.'],
        },
      ],
      blockedReasons: [
        {
          code: 'compliance_evidence_requested',
          severity: 'warning',
          route_slug: 'compliance',
          notes: ['Upload screenshots of the owned channels.'],
        },
        {
          code: 'governance_state:warning',
          severity: 'warning',
          route_slug: 'compliance',
          notes: ['Governance monitoring is active.'],
        },
      ],
    });

    expect(tasks.map((item) => item.kind)).toEqual([
      'disclosure_attestation',
      'evidence_upload',
      'postback_readiness',
      'support_ownership',
      'approved_sources',
    ]);
    expect(tasks.find((item) => item.kind === 'evidence_upload')?.notes).toContain(
      'Upload screenshots of the owned channels.',
    );
    expect(tasks[1]?.status).toBe('action_required');
    expect(tasks[3]?.status).toBe('under_review');
  });

  it('filters blocked reasons by compliance and cases surfaces', () => {
    const reasons = [
      {
        code: 'finance_blocked',
        severity: 'critical',
        route_slug: 'finance',
        notes: ['Payout actions remain blocked.'],
      },
      {
        code: 'compliance_blocked',
        severity: 'critical',
        route_slug: 'compliance',
        notes: ['Declarations remain blocked.'],
      },
      {
        code: 'technical_blocked',
        severity: 'critical',
        route_slug: 'integrations',
        notes: ['Technical launch tooling remains limited.'],
      },
    ];

    expect(getComplianceRestrictionReasons(reasons).map((item) => item.code)).toEqual([
      'compliance_blocked',
    ]);
    expect(getCasesRestrictionReasons(reasons).map((item) => item.code)).toEqual([
      'finance_blocked',
      'compliance_blocked',
      'technical_blocked',
    ]);
  });
});
