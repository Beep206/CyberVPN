import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('next-intl', () => ({
  useTranslations: (namespace?: string) => {
    const navigationMessages: Record<string, string> = {
      application: 'APPLICATION',
      applicationHint: 'Onboarding, review, requested info',
      organization: 'ORGANIZATION',
      organizationHint: 'Business profile, domains, contacts',
      team: 'TEAM & ACCESS',
      teamHint: 'Members, roles, workspace security',
      programs: 'PROGRAMS',
      programsHint: 'Lanes, restrictions, approvals',
      legal: 'CONTRACTS & LEGAL',
      legalHint: 'Terms, policies, acceptance history',
      codes: 'CODES & TRACKING',
      codesHint: 'Links, QR, attribution setup',
      campaigns: 'CAMPAIGNS',
      campaignsHint: 'Assets, enablement, approvals',
      conversions: 'CONVERSIONS',
      conversionsHint: 'Orders, leads, commission context',
      analytics: 'ANALYTICS',
      analyticsHint: 'Performance, exports, explainability',
      finance: 'FINANCE',
      financeHint: 'Statements, payout readiness, holds',
      compliance: 'COMPLIANCE',
      complianceHint: 'Declarations, policy, governance',
      integrations: 'INTEGRATIONS',
      integrationsHint: 'Tokens, postbacks, delivery logs',
      cases: 'SUPPORT & CASES',
      casesHint: 'Messages, disputes, requests',
      notifications: 'INBOX',
      notificationsHint: 'Status changes and alerts',
      settings: 'SETTINGS',
      settingsHint: 'MFA, sessions, preferences',
      reseller: 'RESELLER CONSOLE',
      resellerHint: 'Storefront and distribution scope',
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

describe('CommandCenterPanels', () => {
  it('renders section links and live operational streams', () => {
    render(<CommandCenterPanels />);

    expect(screen.getByLabelText('Command center operations')).toBeInTheDocument();
    expect(screen.getByText('CONTROL DOMAINS')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /APPLICATION/i })).toHaveAttribute(
      'href',
      '/application',
    );
    expect(screen.getByRole('link', { name: /FINANCE/i })).toHaveAttribute(
      'href',
      '/finance',
    );
    expect(screen.getByText('$120.00')).toBeInTheDocument();
    expect(screen.getAllByText(/Cryptobot/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Provider: Stripe/i)).toBeInTheDocument();
    expect(screen.getByText('Approve Withdrawal')).toBeInTheDocument();
    expect(screen.getByText('signature mismatch')).toBeInTheDocument();
    expect(screen.getAllByText('Invalid').length).toBeGreaterThan(0);
  });
});
