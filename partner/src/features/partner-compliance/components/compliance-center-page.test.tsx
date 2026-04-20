import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createPartnerPortalScenarioState,
  type PartnerPortalState,
} from '@/features/partner-portal-state/lib/portal-state';

const submitWorkspaceTrafficDeclaration = vi.fn();
const submitWorkspaceCreativeApproval = vi.fn();

const mockRuntimeState = vi.fn<
  () => {
    state: PartnerPortalState & {
      trafficDeclarations: Array<{
        id: string;
        kind: string;
        status: string;
        scopeLabel: string;
        updatedAt: string;
        notes: string[];
      }>;
    };
    isCanonicalWorkspace: boolean;
    activeWorkspace: { display_name: string } | null;
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
      'performance_media',
      'traffic_manager',
      'R4',
    ),
    trafficDeclarations: [
      {
        id: 'approved-sources:workspace_001',
        kind: 'approved_sources',
        status: 'complete',
        scopeLabel: 'Workspace-owned traffic sources',
        updatedAt: '2026-04-18T10:00:00Z',
        notes: ['Declared sources are clear for the current workspace state.'],
      },
    ],
  },
  isCanonicalWorkspace: true,
  activeWorkspace: { id: 'workspace_001', display_name: 'North Star Growth Studio' },
  blockedReasons: [
    {
      code: 'compliance_evidence_requested',
      severity: 'warning',
      route_slug: 'compliance',
      notes: ['Upload screenshots of the owned channels.'],
    },
  ],
  notificationPreferences: null,
  queries: {},
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string, values?: Record<string, string>) => {
    if (key === 'declarations.scope') {
      return `Scope: ${values?.value ?? ''}`;
    }
    return key;
  },
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...rest
  }: {
    children: ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
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

vi.mock('@/lib/api/partner-portal', () => ({
  partnerPortalApi: {
    submitWorkspaceTrafficDeclaration: (...args: unknown[]) =>
      submitWorkspaceTrafficDeclaration(...args),
    submitWorkspaceCreativeApproval: (...args: unknown[]) =>
      submitWorkspaceCreativeApproval(...args),
  },
}));

import { ComplianceCenterPage } from './compliance-center-page';

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ComplianceCenterPage />
    </QueryClientProvider>,
  );
}

describe('ComplianceCenterPage', () => {
  beforeEach(() => {
    submitWorkspaceTrafficDeclaration.mockReset();
    submitWorkspaceCreativeApproval.mockReset();
    submitWorkspaceTrafficDeclaration.mockResolvedValue({
      data: { id: 'decl_001' },
    });
    submitWorkspaceCreativeApproval.mockResolvedValue({
      data: { id: 'creative_001' },
    });
  });

  it('renders backend-owned traffic declarations in the portal compliance surface', () => {
    renderPage();

    expect(screen.getByText('declarations.title')).toBeInTheDocument();
    expect(screen.getAllByText('complianceTaskKinds.approved_sources')).toHaveLength(2);
    expect(screen.getByText('Scope: Workspace-owned traffic sources')).toBeInTheDocument();
    expect(screen.getByText('Declared sources are clear for the current workspace state.')).toBeInTheDocument();
    expect(screen.getAllByText('complianceTaskStatuses.complete').length).toBeGreaterThan(0);
  });

  it('submits workspace-scoped traffic declarations and creative approvals from the compliance center', async () => {
    const user = userEvent.setup();

    renderPage();

    await user.selectOptions(
      screen.getByLabelText('actions.traffic.kindLabel'),
      'postback_readiness',
    );
    await user.type(
      screen.getByLabelText('actions.traffic.scopeLabel'),
      'Tracking and postback handoff',
    );
    await user.type(
      screen.getByLabelText('actions.traffic.detailsLabel'),
      'Webhook destination prepared for review.',
    );
    await user.click(screen.getByRole('button', { name: 'actions.traffic.submit' }));

    await waitFor(() => {
      expect(submitWorkspaceTrafficDeclaration).toHaveBeenCalledWith('workspace_001', {
        declaration_kind: 'postback_readiness',
        scope_label: 'Tracking and postback handoff',
        declaration_payload: {
          summary: 'Webhook destination prepared for review.',
        },
        notes: ['Webhook destination prepared for review.'],
      });
    });

    expect(await screen.findByText('actions.traffic.success')).toBeInTheDocument();

    await user.type(
      screen.getByLabelText('actions.creative.scopeLabel'),
      'Creative and claims posture',
    );
    await user.type(
      screen.getByLabelText('actions.creative.referenceLabel'),
      'banner-001',
    );
    await user.type(
      screen.getByLabelText('actions.creative.detailsLabel'),
      'Creative requires claims validation.',
    );
    await user.click(screen.getByRole('button', { name: 'actions.creative.submit' }));

    await waitFor(() => {
      expect(submitWorkspaceCreativeApproval).toHaveBeenCalledWith('workspace_001', {
        scope_label: 'Creative and claims posture',
        creative_ref: 'banner-001',
        approval_payload: {
          summary: 'Creative requires claims validation.',
        },
        notes: ['Creative requires claims validation.'],
      });
    });

    expect(await screen.findByText('actions.creative.success')).toBeInTheDocument();
  });
});
