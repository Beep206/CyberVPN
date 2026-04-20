'use client';

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createPartnerPortalScenarioState,
  type PartnerPortalState,
} from '@/features/partner-portal-state/lib/portal-state';

const scheduleWorkspaceReportExport = vi.fn();

const mockRuntimeState = vi.fn<
  () => {
    state: PartnerPortalState;
    isCanonicalWorkspace: boolean;
    activeWorkspace: { id: string; display_name: string } | null;
    notificationPreferences: null;
    queries: Record<string, null>;
  }
>(() => ({
  state: {
    ...createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'workspace_admin',
      'R4',
    ),
    reportExports: [
      {
        id: 'statement-export',
        kind: 'statement_export',
        status: 'scheduled',
        cadence: 'per_statement_close',
        notes: ['Frozen statement snapshots only.'],
        availableActions: ['schedule_export'],
        threadEvents: [
          {
            id: 'event_001',
            actionKind: 'partner_export_requested',
            message: 'Previous export request recorded.',
            createdAt: '2026-04-19T10:00:00Z',
            createdByAdminUserId: 'admin_001',
          },
        ],
        lastRequestedAt: '2026-04-19T10:00:00Z',
      },
    ],
  },
  isCanonicalWorkspace: true,
  activeWorkspace: { id: 'workspace_001', display_name: 'North Star Growth Studio' },
  notificationPreferences: null,
  queries: {},
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string, values?: Record<string, string>) => {
    if (key === 'exports.cadence') {
      return `Cadence: ${values?.value ?? ''}`;
    }
    if (key === 'exports.lastRequested') {
      return `Last requested: ${values?.value ?? ''}`;
    }
    if (key === 'exports.requestSuccess') {
      return `Scheduled ${values?.kind ?? ''}`;
    }
    if (key === 'exports.requestMessage') {
      return `Request ${values?.kind ?? ''}`;
    }
    return key;
  },
}));

vi.mock('@/components/ui/button', () => ({
  Button: ({
    children,
    ...rest
  }: {
    children: ReactNode;
    [key: string]: unknown;
  }) => <button {...rest}>{children}</button>,
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
    scheduleWorkspaceReportExport: (...args: unknown[]) =>
      scheduleWorkspaceReportExport(...args),
  },
}));

import { AnalyticsExportsPage } from './analytics-exports-page';

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <AnalyticsExportsPage />
    </QueryClientProvider>,
  );
}

describe('AnalyticsExportsPage', () => {
  beforeEach(() => {
    scheduleWorkspaceReportExport.mockReset();
    scheduleWorkspaceReportExport.mockResolvedValue({
      data: {
        id: 'statement-export',
      },
    });
  });

  it('renders backend-owned export lifecycle details', () => {
    renderPage();

    expect(screen.getByText('reportExportKinds.statement_export')).toBeInTheDocument();
    expect(screen.getByText('Frozen statement snapshots only.')).toBeInTheDocument();
    expect(screen.getByText('Previous export request recorded.')).toBeInTheDocument();
    expect(screen.getByText(/Last requested:/)).toBeInTheDocument();
  });

  it('requests workspace export scheduling through the canonical route', async () => {
    const user = userEvent.setup();

    renderPage();
    await user.click(screen.getByRole('button', { name: 'exports.requestAction' }));

    await waitFor(() => {
      expect(scheduleWorkspaceReportExport).toHaveBeenCalledWith(
        'workspace_001',
        'statement-export',
        {
          message: 'Request reportExportKinds.statement_export',
          request_payload: {
            request_origin: 'partner_portal_reporting_surface',
            requested_surface_mode: 'full',
          },
        },
      );
    });

    expect(await screen.findByText(
      'Scheduled reportExportKinds.statement_export',
    )).toBeInTheDocument();
  });
});
