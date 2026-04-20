import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createPartnerPortalScenarioState,
  type PartnerPortalState,
} from '@/features/partner-portal-state/lib/portal-state';

const respondToWorkspaceReviewRequest = vi.fn();
const respondToWorkspaceCase = vi.fn();
const markWorkspaceCaseReadyForOps = vi.fn();

const mockRuntimeState = vi.fn<
  () => {
    state: PartnerPortalState & {
      activeWorkspaceDisplayName?: string | null;
      activeWorkspaceId?: string | null;
    };
    isCanonicalWorkspace: boolean;
    activeWorkspace: { id: string; display_name: string } | null;
    blockedReasons: Array<{
      code: string;
      severity: string;
      route_slug: string | null;
      notes: string[];
    }>;
    notificationPreferences: null;
    queries: Record<string, null>;
  }
>(() => ({
  state: {
    ...createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'workspace_owner',
      'R4',
    ),
    reviewRequests: [
      {
        id: 'finance-profile:workspace_001',
        kind: 'finance_profile',
        dueDate: '2026-04-25T10:00:00Z',
        status: 'open',
        availableActions: ['submit_response'],
        threadEvents: [],
      },
    ],
    cases: [
      {
        id: 'case:finance-profile:workspace_001',
        kind: 'finance_onboarding',
        status: 'waiting_on_partner',
        updatedAt: '2026-04-25T10:00:00Z',
        notes: ['Review request kind: finance_profile'],
        availableActions: ['reply', 'mark_ready_for_ops'],
        threadEvents: [],
      },
    ],
    activeWorkspaceDisplayName: 'North Star Growth Studio',
    activeWorkspaceId: 'workspace_001',
  },
  isCanonicalWorkspace: true,
  activeWorkspace: {
    id: 'workspace_001',
    display_name: 'North Star Growth Studio',
  },
  blockedReasons: [
    {
      code: 'finance_blocked',
      severity: 'critical',
      route_slug: 'finance',
      notes: ['Payout-bearing actions remain blocked until finance readiness is restored.'],
    },
  ],
  notificationPreferences: null,
  queries: {},
}));

vi.mock('@/features/partner-portal-state/components/partner-route-guard', () => ({
  PartnerRouteGuard: ({
    children,
  }: {
    children: (access: 'read' | 'write' | 'admin' | 'none') => ReactNode;
  }) => <>{children('admin')}</>,
}));

vi.mock('@/features/partner-portal-state/lib/use-partner-portal-runtime-state', () => ({
  usePartnerPortalRuntimeState: () => mockRuntimeState(),
}));

vi.mock('@/components/ui/button', () => ({
  Button: ({
    children,
    ...props
  }: {
    children: ReactNode;
    [key: string]: unknown;
  }) => <button {...props}>{children}</button>,
}));

vi.mock('@/lib/api/partner-portal', () => ({
  partnerPortalApi: {
    respondToWorkspaceReviewRequest: (...args: unknown[]) =>
      respondToWorkspaceReviewRequest(...args),
    respondToWorkspaceCase: (...args: unknown[]) =>
      respondToWorkspaceCase(...args),
    markWorkspaceCaseReadyForOps: (...args: unknown[]) =>
      markWorkspaceCaseReadyForOps(...args),
  },
}));

import { PartnerCasesPage } from './partner-cases-page';

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <PartnerCasesPage />
    </QueryClientProvider>,
  );
}

describe('PartnerCasesPage', () => {
  beforeEach(() => {
    respondToWorkspaceReviewRequest.mockReset();
    respondToWorkspaceCase.mockReset();
    markWorkspaceCaseReadyForOps.mockReset();
    respondToWorkspaceReviewRequest.mockResolvedValue({
      data: { id: 'event_001' },
    });
    respondToWorkspaceCase.mockResolvedValue({
      data: { id: 'event_002' },
    });
    markWorkspaceCaseReadyForOps.mockResolvedValue({
      data: { id: 'event_003' },
    });
  });

  it('keeps workspace support routing separate from storefront customer messaging', () => {
    renderPage();

    expect(screen.getByText('Workspace support lane')).toBeInTheDocument();
    expect(screen.getByText('North Star Growth Studio ops and compliance routing')).toBeInTheDocument();
    expect(screen.getByText('Branded storefront support remains separate')).toBeInTheDocument();
    expect(
      screen.getByText(/Do not answer customer checkout or access requests from workspace support threads/i),
    ).toBeInTheDocument();
  });

  it('submits canonical review-request and case workflow actions from the portal surface', async () => {
    const user = userEvent.setup();

    renderPage();

    await user.type(
      screen.getByLabelText('requestedInfo.responseLabel'),
      'Uploaded payout profile evidence and settlement contacts.',
    );
    await user.click(
      screen.getByRole('button', { name: 'requestedInfo.submitCanonicalAction' }),
    );

    await waitFor(() => {
      expect(respondToWorkspaceReviewRequest).toHaveBeenCalledWith(
        'workspace_001',
        'finance-profile:workspace_001',
        {
          message: 'Uploaded payout profile evidence and settlement contacts.',
          response_payload: {
            response_origin: 'partner_portal_cases_surface',
          },
        },
      );
    });

    expect(await screen.findByText('requestedInfo.success')).toBeInTheDocument();

    await user.type(
      screen.getByLabelText('caseList.responseLabel'),
      'Finance package is complete and ready for partner ops review.',
    );
    await user.click(screen.getByRole('button', { name: 'caseList.replyAction' }));

    await waitFor(() => {
      expect(respondToWorkspaceCase).toHaveBeenCalledWith(
        'workspace_001',
        'case:finance-profile:workspace_001',
        {
          message: 'Finance package is complete and ready for partner ops review.',
          response_payload: {
            response_origin: 'partner_portal_cases_surface',
            workflow_action: 'reply',
          },
        },
      );
    });

    expect(await screen.findByText('caseList.replySuccess')).toBeInTheDocument();

    await user.clear(screen.getByLabelText('caseList.responseLabel'));
    await user.type(
      screen.getByLabelText('caseList.responseLabel'),
      'Case is packaged and ready for ops handoff.',
    );
    await user.click(screen.getByRole('button', { name: 'caseList.readyAction' }));

    await waitFor(() => {
      expect(markWorkspaceCaseReadyForOps).toHaveBeenCalledWith(
        'workspace_001',
        'case:finance-profile:workspace_001',
        {
          message: 'Case is packaged and ready for ops handoff.',
          response_payload: {
            response_origin: 'partner_portal_cases_surface',
            workflow_action: 'mark_ready_for_ops',
          },
        },
      );
    });

    expect(await screen.findByText('caseList.readySuccess')).toBeInTheDocument();
  });
});
