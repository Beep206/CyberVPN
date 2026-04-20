import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createPartnerPortalScenarioState,
  type PartnerPortalState,
} from '@/features/partner-portal-state/lib/portal-state';

const mockRuntimeState = vi.fn<
  () => {
    state: PartnerPortalState;
    programsSnapshot: {
      canonicalSource: string;
      primaryLaneKey: string | null;
      laneMemberships: Array<{
        laneKey: string;
        membershipStatus: string;
        ownerContextLabel: string;
        pilotCohortId: string | null;
        pilotCohortStatus: string | null;
        runbookGateStatus: string | null;
        blockingReasonCodes: string[];
        warningReasonCodes: string[];
        restrictionNotes: string[];
        readinessNotes: string[];
        updatedAt: string;
      }>;
      readinessItems: Array<{
        key: string;
        status: string;
        blockingReasonCodes: string[];
        notes: string[];
      }>;
      updatedAt: string;
    } | null;
    isCanonicalWorkspace: boolean;
    activeWorkspace: { id: string; display_name: string } | null;
    notificationPreferences: null;
    queries: Record<string, null>;
  }
>(() => ({
  state: {
    ...createPartnerPortalScenarioState(
      'active',
      'reseller_api',
      'workspace_owner',
      'R4',
    ),
    laneMemberships: [
      {
        lane: 'reseller_api',
        status: 'approved_active',
        assignedManager: 'Legacy Reseller Manager',
        restrictions: ['Legacy local programs state should not leak into canonical rendering.'],
      },
    ],
    financeReadiness: 'not_started',
    complianceReadiness: 'not_started',
    technicalReadiness: 'not_required',
    updatedAt: '2026-04-19T08:00:00Z',
  },
  programsSnapshot: {
    canonicalSource: 'pilot_cohorts',
    primaryLaneKey: 'creator_affiliate',
    laneMemberships: [
      {
        laneKey: 'creator_affiliate',
        membershipStatus: 'approved_active',
        ownerContextLabel: 'Partner Ops',
        pilotCohortId: 'cohort_001',
        pilotCohortStatus: 'active',
        runbookGateStatus: 'green',
        blockingReasonCodes: [],
        warningReasonCodes: [],
        restrictionNotes: ['Lane has an explicit canonical cohort and readiness trail.'],
        readinessNotes: ['Owner context: Partner Ops.', 'Runbook gate: green.'],
        updatedAt: '2026-04-19T09:15:00Z',
      },
      {
        laneKey: 'performance_media',
        membershipStatus: 'pending',
        ownerContextLabel: 'Traffic Desk',
        pilotCohortId: 'cohort_002',
        pilotCohortStatus: 'scheduled',
        runbookGateStatus: 'red',
        blockingReasonCodes: ['traffic_declaration_incomplete', 'creative_approval_incomplete'],
        warningReasonCodes: ['settlement_shadow_requires_caution'],
        restrictionNotes: ['Traffic declarations are still incomplete for this lane.'],
        readinessNotes: ['Owner context: Traffic Desk.', 'Runbook gate: red.'],
        updatedAt: '2026-04-19T09:20:00Z',
      },
    ],
    readinessItems: [
      {
        key: 'finance',
        status: 'ready',
        blockingReasonCodes: [],
        notes: ['At least one verified and approved payout account is available.'],
      },
      {
        key: 'compliance',
        status: 'evidence_requested',
        blockingReasonCodes: ['traffic_declaration_incomplete'],
        notes: ['Traffic declarations are still incomplete for this lane.'],
      },
      {
        key: 'technical',
        status: 'in_progress',
        blockingReasonCodes: ['postback_pending'],
        notes: ['Postback credential is missing or rotation is still required before rollout.'],
      },
    ],
    updatedAt: '2026-04-19T09:20:00Z',
  },
  isCanonicalWorkspace: true,
  activeWorkspace: {
    id: 'workspace_001',
    display_name: 'North Star Growth Studio',
  },
  notificationPreferences: null,
  queries: {},
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-US',
  useTranslations: () => (key: string, values?: Record<string, string>) => {
    if (key === 'lanes.ownerContext') {
      return `Owner context: ${values?.value ?? ''}`;
    }
    if (key === 'lanes.cohortStatus') {
      return `Pilot cohort: ${values?.value ?? ''}`;
    }
    if (key === 'readiness.lastUpdated') {
      return `Last canonical update: ${values?.value ?? ''}`;
    }
    if (key === 'links.workspaceContext') {
      return `Workspace context: ${values?.value ?? ''}`;
    }
    return key;
  },
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...props
  }: {
    children: ReactNode;
    href: string;
    [key: string]: unknown;
  }) => <a href={href} {...props}>{children}</a>,
}));

vi.mock('@/features/partner-portal-state/components/partner-route-guard', () => ({
  PartnerRouteGuard: ({
    children,
  }: {
    children: (access: 'read' | 'write' | 'admin' | 'none') => ReactNode;
  }) => <>{children('write')}</>,
}));

vi.mock('@/features/partner-portal-state/lib/use-partner-portal-runtime-state', () => ({
  usePartnerPortalRuntimeState: () => mockRuntimeState(),
}));

import { ProgramsPage } from './programs-page';

describe('ProgramsPage', () => {
  beforeEach(() => {
    mockRuntimeState.mockClear();
  });

  it('renders canonical programs posture instead of falling back to local lane state', () => {
    render(<ProgramsPage />);

    expect(screen.getByText('summary.currentLane')).toBeInTheDocument();
    expect(screen.getAllByText('laneLabels.creator_affiliate').length).toBeGreaterThan(0);
    expect(screen.getByText('pilot_cohorts')).toBeInTheDocument();
    expect(screen.getByText('Owner context: Partner Ops')).toBeInTheDocument();
    expect(screen.getAllByText('traffic_declaration_incomplete').length).toBeGreaterThan(0);
    expect(screen.getByText('settlement_shadow_requires_caution')).toBeInTheDocument();
    expect(screen.getAllByText('readinessLabels.compliance').length).toBeGreaterThan(0);
    expect(
      screen.getByText('At least one verified and approved payout account is available.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Workspace context: North Star Growth Studio')).toBeInTheDocument();
    expect(screen.queryByText('Legacy Reseller Manager')).not.toBeInTheDocument();
  });
});
