import { render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '@/stores/auth-store';

vi.mock('next-intl', () => ({
  useTranslations: (namespace?: string) => {
    const navigationMessages: Record<string, string> = {
      customers: 'CUSTOMERS',
      customersHint: 'Lifecycle, support, accounts',
      messaging: 'MESSAGING',
      messagingHint: 'Private dialogs, notes, presence',
      support: 'SUPPORT',
      supportHint: 'Inbox, replies, internal notes',
      commerce: 'COMMERCE',
      commerceHint: 'Plans, payments, wallets',
      growth: 'GROWTH',
      growthHint: 'Promo, invites, referrals',
      infrastructure: 'INFRASTRUCTURE',
      infrastructureHint: 'Servers, nodes, rollouts',
      security: 'SECURITY',
      securityHint: 'Sessions, 2FA, trust',
      governance: 'GOVERNANCE',
      governanceHint: 'Audit, webhooks, staff access',
      integrations: 'INTEGRATIONS',
      integrationsHint: 'Telegram, push, realtime',
      unavailableForRole: 'Unavailable for current role',
    };

    const dashboardMessages: Record<string, string> = {
      opsGridLabel: 'Command center operations',
      sectionMapTitle: 'CONTROL DOMAINS',
      sectionMapDescription: 'Top-level staff surfaces',
      'sectionReadiness.strong': 'ready',
      'sectionReadiness.partial': 'partial',
      'sectionReadiness.blocked': 'blocked',
      sectionSignalsReady: 'signals ready',
      sectionModulesNext: 'next modules',
      withdrawalsTitle: 'WITHDRAWAL QUEUE',
      withdrawalsDescription: 'Pending withdrawals',
      paymentsTitle: 'RECENT PAYMENTS',
      paymentsDescription: 'Newest payments',
      auditTitle: 'AUDIT STREAM',
      auditDescription: 'Recent privileged actions',
      webhooksTitle: 'WEBHOOK STREAM',
      webhooksDescription: 'Latest callbacks',
      actionQueuesTitle: 'ACTION QUEUES',
      actionQueuesDescription: 'Live operator workload',
      myWorkspaceTitle: 'MY WORKSPACE',
      myWorkspaceDescription: 'Role-specific actions',
      myWorkspaceBadge: 'ROLE AWARE',
      workspaceRoleLabel: 'Role',
      workspaceEnabledActions: 'Available routes',
      workspaceRestrictedActions: 'Restricted routes',
      workspacePermissionCount: 'Permissions',
      workspaceAvailableNow: 'Available now',
      workspaceReadActions: 'read',
      workspaceWriteActions: 'write',
      workspaceNoActions: 'No actions',
      'workspaceRisk.read': 'Read surface',
      'workspaceRisk.write': 'Operator action',
      'workspaceRisk.danger': 'Sensitive action',
      openQueue: 'Open',
      queueUnavailableForRole: 'Role gated',
      'queueStates.active': 'Needs action',
      'queueStates.empty': 'Clear',
      'queueStates.error': 'Unavailable',
      'queueStates.loading': 'Syncing',
      'queueStates.unavailable': 'Role gated',
      'actionQueues.withdrawals.title': 'Withdrawal approvals',
      'actionQueues.withdrawals.description': 'Pending wallet withdrawals',
      'actionQueues.withdrawals.metric': 'pending withdrawals',
      'actionQueues.support.title': 'Support handoffs',
      'actionQueues.support.description': 'Tickets waiting for support',
      'actionQueues.support.metric': 'pending support tickets',
      'actionQueues.securityReviews.title': 'Risk reviews',
      'actionQueues.securityReviews.description': 'Security queue',
      'actionQueues.securityReviews.metric': 'open reviews',
      'actionQueues.growthAbuse.title': 'Growth abuse signals',
      'actionQueues.growthAbuse.description': 'Growth queue',
      'actionQueues.growthAbuse.metric': 'open signal groups',
      'actionQueues.webhookFailures.title': 'Webhook failures',
      'actionQueues.webhookFailures.description': 'Invalid callbacks',
      'actionQueues.webhookFailures.metric': 'invalid callbacks',
      'empty.withdrawals': 'No withdrawals',
      'empty.payments': 'No payments',
      'empty.audit': 'No audit',
      'empty.webhooks': 'No webhooks',
      'errors.load': 'Panel error',
      'labels.items': 'items',
      'labels.method': 'Method',
      'labels.provider': 'Provider',
      'labels.processedAt': 'Processed',
      'labels.unknown': 'Unknown',
      'labels.unassigned': 'Unassigned',
      'labels.valid': 'Valid',
      'labels.invalid': 'Invalid',
      'labels.noError': 'No errors',
    };

    const messages = namespace === 'Navigation' ? navigationMessages : dashboardMessages;
    return (key: string) => messages[key] ?? key;
  },
}));

vi.mock('@/features/admin-shell/hooks/use-admin-action-queues', () => ({
  formatAdminQueueBadge: (count: number) => String(count),
  useAdminActionQueues: () => ({
    badges: {
      'commerce-withdrawals': 3,
      support: 2,
    },
    queues: [
      {
        id: 'withdrawals',
        navItemId: 'commerce-withdrawals',
        href: '/commerce/withdrawals',
        titleKey: 'actionQueues.withdrawals.title',
        descriptionKey: 'actionQueues.withdrawals.description',
        metricKey: 'actionQueues.withdrawals.metric',
        count: 3,
        state: 'active',
        tone: 'warning',
        risk: 'write',
        requiredPermissions: ['payment_read'],
      },
      {
        id: 'support',
        navItemId: 'support',
        href: '/support?status=pending_support',
        titleKey: 'actionQueues.support.title',
        descriptionKey: 'actionQueues.support.description',
        metricKey: 'actionQueues.support.metric',
        count: 0,
        state: 'empty',
        tone: 'success',
        risk: 'write',
        requiredPermissions: ['support_ticket_read'],
      },
    ],
  }),
}));

vi.mock('../../hooks/useDashboardData', () => ({
  usePendingWithdrawals: () => ({
    data: [
      {
        id: 'withdrawal-12345678',
        amount: 120,
        currency: 'USD',
        method: 'cryptobot',
        status: 'pending',
        created_at: '2026-04-10T10:00:00Z',
      },
    ],
    isPending: false,
    isError: false,
  }),
  useRecentPayments: () => ({
    data: [
      {
        id: 'payment-12345678',
        amount: 49.99,
        currency: 'USD',
        provider: 'stripe',
        status: 'completed',
        created_at: '2026-04-10T09:00:00Z',
      },
    ],
    isPending: false,
    isError: false,
  }),
  useRecentAuditLogs: () => ({
    data: [
      {
        id: 'audit-12345678',
        action: 'approve_withdrawal',
        entity_type: 'withdrawal',
        entity_id: 'withdrawal-12345678',
        admin_id: 'admin-12345678',
        ip_address: '127.0.0.1',
        created_at: '2026-04-10T09:30:00Z',
      },
    ],
    isPending: false,
    isError: false,
  }),
  useRecentWebhookLogs: () => ({
    data: [
      {
        id: 'webhook-12345678',
        source: 'cryptobot',
        event_type: 'invoice_paid',
        is_valid: false,
        processed_at: '2026-04-10T09:45:00Z',
        error_message: 'signature mismatch',
        created_at: '2026-04-10T09:44:00Z',
      },
    ],
    isPending: false,
    isError: false,
  }),
}));

import { CommandCenterPanels } from '../CommandCenterPanels';

type TestAdminRole = 'admin' | 'finance' | 'viewer';

function setAdminRole(role: TestAdminRole) {
  useAuthStore.setState({
    user: {
      id: `${role}-1`,
      email: `${role}@example.test`,
      role,
      is_active: true,
      is_email_verified: true,
      created_at: '2026-01-01T00:00:00.000Z',
    },
    isAuthenticated: true,
  });
}

function getSectionMapQueries() {
  const panel = screen.getByText('CONTROL DOMAINS').closest('article');

  if (!panel) {
    throw new Error('Missing CONTROL DOMAINS panel');
  }

  return within(panel);
}

function getSectionCard(label: string) {
  const heading = screen.getByText(label);
  const card = heading.closest('a, article');

  if (!card) {
    throw new Error(`Missing section card: ${label}`);
  }

  return card;
}

describe('CommandCenterPanels', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setAdminRole('admin');
  });

  it('renders section links and live operational streams for enabled admin sections', () => {
    render(<CommandCenterPanels />);

    expect(screen.getByLabelText('Command center operations')).toBeInTheDocument();
    expect(screen.getByText('ACTION QUEUES')).toBeInTheDocument();
    expect(screen.getByText('Withdrawal approvals')).toBeInTheDocument();
    expect(screen.getByText('pending withdrawals')).toBeInTheDocument();
    expect(screen.getByText('CONTROL DOMAINS')).toBeInTheDocument();
    const sectionMap = getSectionMapQueries();
    expect(sectionMap.getByRole('link', { name: /CUSTOMERS/i })).toHaveAttribute(
      'href',
      '/customers',
    );
    expect(sectionMap.getByRole('link', { name: /COMMERCE/i })).toHaveAttribute(
      'href',
      '/commerce',
    );
    expect(screen.getByText('$120.00')).toBeInTheDocument();
    expect(screen.getAllByText(/Cryptobot/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Provider: Stripe/i)).toBeInTheDocument();
    expect(screen.getByText('Approve Withdrawal')).toBeInTheDocument();
    expect(screen.getByText('signature mismatch')).toBeInTheDocument();
    expect(screen.getAllByText('Invalid').length).toBeGreaterThan(0);
  });

  it('renders viewer-restricted section cards without clickable links', () => {
    setAdminRole('viewer');

    render(<CommandCenterPanels />);

    expect(screen.getByText('COMMERCE')).toBeInTheDocument();
    const sectionMap = getSectionMapQueries();
    expect(
      sectionMap.queryByRole('link', { name: /COMMERCE/i }),
    ).not.toBeInTheDocument();
    expect(sectionMap.getByRole('link', { name: /CUSTOMERS/i })).toHaveAttribute(
      'href',
      '/customers',
    );
    expect(screen.getAllByText('Unavailable for current role').length).toBeGreaterThan(0);
  });

  it('keeps gated labels on a wrapping full-width row', () => {
    setAdminRole('viewer');

    render(<CommandCenterPanels />);

    const commerceCard = getSectionCard('COMMERCE');
    const gatedLabel = within(commerceCard).getByText('Unavailable for current role');

    expect(commerceCard).toHaveAttribute('data-access-state', 'disabled');
    expect(gatedLabel).toHaveClass('block');
    expect(gatedLabel).toHaveClass('w-full');
    expect(gatedLabel).toHaveClass('wrap-normal');
  });

  it('renders finance-restricted section cards without clickable links', () => {
    setAdminRole('finance');

    render(<CommandCenterPanels />);

    const sectionMap = getSectionMapQueries();
    expect(sectionMap.getByRole('link', { name: /COMMERCE/i })).toHaveAttribute(
      'href',
      '/commerce',
    );
    expect(screen.getByText('INFRASTRUCTURE')).toBeInTheDocument();
    expect(
      sectionMap.queryByRole('link', { name: /INFRASTRUCTURE/i }),
    ).not.toBeInTheDocument();
  });
});
