import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createPartnerPortalScenarioState,
  type PartnerPortalState,
} from '@/features/partner-portal-state/lib/portal-state';

const listPartnerBots = vi.fn();
const getWorkspacePostbackReadiness = vi.fn();
const getWidget = vi.fn();

const mockRuntimeState = vi.fn<
  () => {
    state: PartnerPortalState;
  }
>(() => ({
  state: {
    ...createPartnerPortalScenarioState(
      'active',
      'performance_media',
      'technical_manager',
      'R4',
    ),
    activeWorkspaceId: 'workspace_001',
    technicalReadiness: 'ready',
    integrationCredentials: [
      {
        id: 'cred_001',
        kind: 'reporting_api_token',
        label: 'Workspace reporting token',
        status: 'ready',
        lastRotatedAt: '2026-04-22T10:00:00Z',
        notes: ['Reporting token is ready.'],
      },
    ],
    integrationDeliveryLogs: [
      {
        id: 'delivery_001',
        channel: 'postback',
        status: 'delivered',
        destination: 'postback://workspace_001',
        notes: ['Postback delivery is green.'],
      },
    ],
  },
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string, values?: Record<string, string>) => {
    if (!values) {
      return key;
    }
    return `${key}:${Object.entries(values)
      .map(([name, value]) => `${name}=${value}`)
      .join(',')}`;
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
  }) => <>{children('admin')}</>,
}));

vi.mock('@/features/partner-portal-state/lib/use-partner-portal-runtime-state', () => ({
  usePartnerPortalRuntimeState: () => mockRuntimeState(),
}));

vi.mock('@/lib/api/partner-portal', () => ({
  partnerPortalApi: {
    listPartnerBots: (...args: unknown[]) => listPartnerBots(...args),
    getWorkspacePostbackReadiness: (...args: unknown[]) => getWorkspacePostbackReadiness(...args),
  },
}));

vi.mock('@/lib/api/public-network', () => ({
  publicNetworkApi: {
    getWidget: (...args: unknown[]) => getWidget(...args),
  },
}));

vi.mock('@/widgets/docs-code-block', () => ({
  DocsCodeBlock: ({ code }: { code: string }) => <pre>{code}</pre>,
}));

import { IntegrationsConsolePage } from './integrations-console-page';

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <IntegrationsConsolePage />
    </QueryClientProvider>,
  );
}

describe('IntegrationsConsolePage', () => {
  beforeEach(() => {
    listPartnerBots.mockReset();
    getWorkspacePostbackReadiness.mockReset();
    getWidget.mockReset();

    listPartnerBots.mockResolvedValue({
      data: [
        {
          id: 'bot_001',
          partner_account_id: 'workspace_001',
          bot_key: 'alpha-bot',
          display_name: 'Alpha Bot',
          default_locale: 'en-EN',
          provisioning_path: 'managed_bot',
          token_status: 'missing',
          status: 'failed',
          release_channel: 'stable',
          managed_by_bot_id: null,
          telegram_bot_id: null,
          telegram_username: null,
          provisioning_last_error: 'Webhook binding failed',
          created_at: '2026-04-22T10:00:00Z',
          updated_at: '2026-04-22T10:05:00Z',
          latest_provisioning_job: {
            id: 'job_001',
            partner_bot_id: 'bot_001',
            partner_account_id: 'workspace_001',
            provisioning_path: 'managed_bot',
            job_status: 'manual_intervention_required',
            attempt_count: 1,
            queued_at: '2026-04-22T10:00:00Z',
            created_at: '2026-04-22T10:00:00Z',
            updated_at: '2026-04-22T10:05:00Z',
          },
        },
        {
          id: 'bot_002',
          partner_account_id: 'workspace_001',
          bot_key: 'beta-bot',
          display_name: 'Beta Bot',
          default_locale: 'en-EN',
          provisioning_path: 'manual_token',
          token_status: 'missing',
          status: 'provisioning_requested',
          release_channel: 'stable',
          managed_by_bot_id: null,
          telegram_bot_id: null,
          telegram_username: null,
          created_at: '2026-04-22T10:00:00Z',
          updated_at: '2026-04-22T10:05:00Z',
          latest_provisioning_job: null,
        },
      ],
    });

    getWorkspacePostbackReadiness.mockResolvedValue({
      data: {
        status: 'in_progress',
        delivery_status: 'paused',
        scope_label: 'Tracking and postback handoff',
        credential_id: 'cred_002',
        credential_status: 'ready',
        notes: ['Workspace-scoped postback is waiting for operator promotion.'],
      },
    });

    getWidget.mockResolvedValue({
      data: {
        generatedAt: '2026-04-22T10:00:00Z',
        recommendedHeight: 420,
        summary: {
          status: 'online',
          currentAvailabilityPct: 99.95,
          onlineServers: 120,
          monthlyTrafficBytes: 1230000000,
        },
      },
    });
  });

  it('renders live provisioning readiness with postback posture and operator notes', async () => {
    renderPage();

    expect(await screen.findByText('readiness.title')).toBeInTheDocument();

    await waitFor(() => {
      expect(listPartnerBots).toHaveBeenCalledWith({
        partner_account_id: 'workspace_001',
        limit: 20,
        offset: 0,
      });
      expect(getWorkspacePostbackReadiness).toHaveBeenCalledWith('workspace_001');
    });

    expect(screen.getByText('readiness.notes.managed_path_operator_handoff')).toBeInTheDocument();
    expect(screen.getByText('readiness.notes.manual_path_available')).toBeInTheDocument();
    expect(screen.getByText('readiness.notes.operator_attention_required')).toBeInTheDocument();
    expect(screen.getByText('readiness.notes.postback_under_review')).toBeInTheDocument();
    expect(screen.getByText('readiness.cards.deliveryStatus:value=paused')).toBeInTheDocument();
    expect(screen.getByText('readiness.snapshot.scope')).toBeInTheDocument();
    expect(screen.getAllByText('bots.binding:value=bots.bindingPending').length).toBeGreaterThan(0);
    expect(screen.getByText('Workspace-scoped postback is waiting for operator promotion.')).toBeInTheDocument();
  });
});
