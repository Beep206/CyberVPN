import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PublicNetworkEmbedCard } from '../public-network-embed-card';

const { getWidgetMock } = vi.hoisted(() => ({
  getWidgetMock: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string, values?: Record<string, string>) => {
    const dictionary: Record<string, string> = {
      eyebrow: 'CYBERVPN PUBLIC NETWORK PROOF',
      title: 'Network Widget',
      description: 'Sanitized live network proof for partner embeds.',
      loading: 'Loading public network widget...',
      error: "The widget couldn't load the public network snapshot.",
      focusRegion: 'Focused region',
      topRegions: 'Top regions',
      'metrics.availability': 'Availability',
      'metrics.onlineServers': 'Online servers',
      'metrics.liveUsers': 'Live users',
      'metrics.monthlyTraffic': 'Monthly traffic',
      'statusValues.online': 'ONLINE',
      'statusValues.degraded': 'DEGRADED',
      'statusValues.major_outage': 'MAJOR OUTAGE',
      'actions.fullMap': 'Open full map',
      'actions.statusPage': 'Status page',
    };

    if (key === 'freshness') {
      return `Updated ${values?.value ?? ''}`;
    }
    if (key === 'incidents') {
      return `Incidents: ${values?.value ?? ''}`;
    }
    if (key === 'regionServers') {
      return `Online servers: ${values?.value ?? ''}`;
    }
    if (key === 'regionUsers') {
      return `Live users: ${values?.value ?? ''}`;
    }

    return dictionary[key] ?? key;
  },
}));

vi.mock('@/lib/api', () => ({
  publicNetworkApi: {
    getWidget: getWidgetMock,
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('PublicNetworkEmbedCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders widget metrics and focused region from the dedicated widget endpoint', async () => {
    getWidgetMock.mockResolvedValue({
      data: {
        schemaVersion: 'public-network-widget.v1',
        generatedAt: '2026-04-22T12:00:00Z',
        expiresAt: '2026-04-22T12:01:00Z',
        freshnessStatus: 'fresh',
        widgetType: 'network_card',
        locale: 'en-EN',
        themeVariant: 'cyber',
        recommendedHeight: 420,
        summary: {
          status: 'degraded',
          currentAvailabilityPct: 99.4,
          onlineServers: 24,
          activeUsers: 278,
          monthlyTrafficBytes: 5 * 1024 ** 4,
          incidentsCount: 1,
        },
        focusRegion: {
          id: 'de',
          countryCode: 'DE',
          publicName: 'DE',
          status: 'online',
          totalServers: 4,
          onlineServers: 4,
          activeUsers: 66,
          totalTrafficBytes: 500_000_000,
        },
        topRegions: [
          {
            rank: 1,
            id: 'de',
            countryCode: 'DE',
            publicName: 'DE',
            status: 'online',
            totalServers: 4,
            onlineServers: 4,
            activeUsers: 66,
            totalTrafficBytes: 500_000_000,
          },
        ],
      },
    });

    render(
      <PublicNetworkEmbedCard locale="en-EN" themeVariant="cyber" widgetType="network_card" regionId="de" />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByText('Network Widget')).toBeInTheDocument();
    });

    expect(getWidgetMock).toHaveBeenCalledWith({
      locale: 'en-EN',
      themeVariant: 'cyber',
      widgetType: 'network_card',
      regionId: 'de',
    });
    expect(screen.getByText('99.4%')).toBeInTheDocument();
    expect(screen.getByText('5 TB')).toBeInTheDocument();
    expect(screen.getAllByText('Germany').length).toBeGreaterThan(0);
    expect(screen.getByText('Incidents: 1')).toBeInTheDocument();
  });
});
