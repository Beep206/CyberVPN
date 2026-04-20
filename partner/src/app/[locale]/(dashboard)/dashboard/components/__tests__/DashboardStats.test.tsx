import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('next-intl', () => ({
  useTranslations: () => {
    const messages: Record<string, string> = {
      'opsGridLabel': 'Command center operations',
      'cards.health.title': 'PLATFORM HEALTH',
      'cards.health.description': 'Dependency health',
      'cards.health.healthy': 'HEALTHY',
      'cards.health.componentsHealthy': 'healthy components',
      'cards.health.componentsFailing': 'failing components',
      'cards.servers.title': 'SERVERS ONLINE',
      'cards.servers.description': 'Traffic-ready nodes',
      'cards.users.title': 'ACTIVE USERS',
      'cards.users.description': 'Live customer footprint',
      'cards.bandwidth.title': 'OUTBOUND BANDWIDTH',
      'cards.bandwidth.description': 'Current egress',
      'cards.withdrawals.title': 'PENDING WITHDRAWALS',
      'cards.withdrawals.description': 'Approval queue',
      'labels.totalUsers': 'total users',
      'labels.inbound': 'inbound',
    };

    return (key: string) => messages[key] ?? key;
  },
}));

vi.mock('../../hooks/useDashboardData', () => ({
  useSystemHealth: () => ({
    data: {
      status: 'healthy',
      components: {
        database: { status: 'healthy' },
        redis: { status: 'healthy' },
        remnawave: { status: 'unhealthy' },
      },
    },
    isPending: false,
  }),
  useServerStats: () => ({
    data: {
      online: 18,
      total: 20,
      warning: 1,
      maintenance: 1,
    },
    isPending: false,
  }),
  useSystemStats: () => ({
    data: {
      active_users: 12,
      total_users: 45,
    },
    isPending: false,
  }),
  useBandwidthAnalytics: () => ({
    data: {
      bytes_in: 64 * 1024 * 1024,
      bytes_out: 128 * 1024 * 1024,
    },
    isPending: false,
  }),
  usePendingWithdrawals: () => ({
    data: [
      { amount: 100, currency: 'USD' },
      { amount: 80, currency: 'USD' },
    ],
    isPending: false,
  }),
}));

import { DashboardStats } from '../DashboardStats';

describe('DashboardStats', () => {
  it('renders the top-level operational KPIs from dashboard hooks', () => {
    render(<DashboardStats />);

    expect(screen.getByLabelText('Command center operations')).toBeInTheDocument();
    expect(screen.getByText('PLATFORM HEALTH')).toBeInTheDocument();
    expect(screen.getByText('HEALTHY')).toBeInTheDocument();
    expect(screen.getByText('18/20')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('128 MB/s')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('2 healthy components / 1 failing components')).toBeInTheDocument();
    expect(screen.getByText('45 total users')).toBeInTheDocument();
  });
});
