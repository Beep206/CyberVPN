import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MetricsHUD } from '../metrics-hud';
import { IncidentLog } from '../incident-log';
import { UptimeMatrix } from '../uptime-matrix';

vi.mock('next-intl', () => ({
  useLocale: () => 'en-US',
  useTranslations: () => (key: string) => {
    const labels: Record<string, string> = {
      'metrics.bandwidth': 'THROUGHPUT',
      'metrics.active_nodes': 'ACTIVE CORES',
      'metrics.uptime': 'UPTIME',
      'metrics.status_nominal': 'ALL SYSTEMS NOMINAL',
      'metrics.status_warning': 'DEGRADED PERFORMANCE',
      'metrics.status_outage': 'MAJOR OUTAGE DETECTED',
      'incidents.title': 'INCIDENT LOG',
      'incidents.empty': 'No active incidents. Network secure.',
      'incidents.view_all': 'VIEW ARCHIVE',
      'history.title': '90-Day History',
      'history.tooltip_date': 'Date',
    };
    return labels[key] ?? key;
  },
}));

describe('status widgets', () => {
  it('renders truthful metric values from public network payloads', () => {
    render(
      <MetricsHUD
        overview={{
          schemaVersion: 'public-network-overview.v1',
          generatedAt: '2026-04-22T12:00:00Z',
          expiresAt: '2026-04-22T12:01:00Z',
          freshnessStatus: 'fresh',
          global: {
            status: 'degraded',
            totalUsers: 1120,
            activeUsers: 278,
            totalServers: 4,
            onlineServers: 2,
            totalNodes: 4,
            distinctCountries: 2,
            totalTrafficBytes: 0,
            monthlyTrafficBytes: 0,
            todayBytesIn: 0,
            todayBytesOut: 3 * 1024 ** 3,
          },
        }}
        uptime={{
          schemaVersion: 'public-network-uptime.v1',
          generatedAt: '2026-04-22T12:00:00Z',
          expiresAt: '2026-04-22T12:01:00Z',
          freshnessStatus: 'fresh',
          summary: {
            status: 'degraded',
            currentAvailabilityPct: 50,
            historyAvailable: false,
            windowDays: 90,
            coverageDays: 0,
          },
          history: [],
        }}
      />,
    );

    expect(screen.getByText('3 GB')).toBeInTheDocument();
    expect(screen.getByText('2 / 4')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('DEGRADED PERFORMANCE')).toBeInTheDocument();
  });

  it('renders incidents and honest uptime fallback without fabricated history', () => {
    render(
      <>
        <IncidentLog
          incidents={[
            {
              id: 'incident-major-outage',
              severity: 'critical',
              status: 'identified',
              publicTitle: 'Regional outage detected',
              publicSummary: '1 of 2 tracked regions currently report no online servers.',
              affectedRegions: ['us'],
              startedAt: '2026-04-22T12:00:00Z',
              resolvedAt: null,
            },
          ]}
        />
        <UptimeMatrix
          history={[]}
          uptime={{
            schemaVersion: 'public-network-uptime.v1',
            generatedAt: '2026-04-22T12:00:00Z',
            expiresAt: '2026-04-22T12:01:00Z',
            freshnessStatus: 'fresh',
            summary: {
              status: 'major_outage',
              currentAvailabilityPct: 50,
              historyAvailable: false,
              windowDays: 90,
              coverageDays: 0,
            },
            history: [],
          }}
        />
      </>,
    );

    expect(
      screen.getByText('1 of 2 tracked regions currently report no online servers.'),
    ).toBeInTheDocument();
    expect(screen.getAllByText('50%').length).toBeGreaterThan(0);
    expect(screen.getAllByText('0 / 90').length).toBeGreaterThan(0);
  });
});
