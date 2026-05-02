import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { AnchorHTMLAttributes, ReactNode } from 'react';
import { DpiResistanceDashboard } from '../dpi-resistance-dashboard';

const { getDpiScoreMock } = vi.hoisted(() => ({
  getDpiScoreMock: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string, values?: Record<string, string | number>) => {
    const dictionary: Record<string, string> = {
      eyebrow: 'CYBERVPN DPI RESISTANCE',
      title: 'DPI Resistance Score',
      description: 'A careful public surface for restrictive-network resilience.',
      loading: 'Loading DPI resistance readiness...',
      error: 'The DPI resistance contract is currently unavailable.',
      enabledState: 'enabled',
      disabledState: 'Public DPI scoring remains gated until enough real probe signal exists.',
      'cards.methodology': 'Methodology',
      'cards.confidence': 'Confidence',
      'cards.countriesTracked': 'Countries tracked',
      'cards.measurementWindow': 'Measurement window',
      'confidenceValues.low': 'LOW',
      'confidenceValues.medium': 'MEDIUM',
      'confidenceValues.high': 'HIGH',
      'gating.eyebrow': 'PUBLIC RELEASE GATE',
      'publishedCountries.title': 'Published country scores',
      'publishedCountries.updated': `Updated ${values?.value ?? ''}`,
      'publishedCountries.score': 'Connect',
      'publishedCountries.baseline': 'Baseline',
      'publishedCountries.handshake': 'Handshake',
      'methodology.eyebrow': 'SIGNAL MODEL',
      'methodology.title': 'What the public score must eventually reflect',
      'methodology.items.connection': 'Connection success rate.',
      'methodology.items.handshake': 'Median handshake latency.',
      'methodology.items.baseline': 'HTTPS/SNI application baseline.',
      'methodology.items.survival': 'Session survival.',
      'methodology.items.freshness': 'Freshness and confidence.',
      'guardrails.eyebrow': 'TRUTHFULNESS POLICY',
      'guardrails.title': 'What this page will not fake',
      'guardrails.items.noMagic': 'No decorative public score.',
      'guardrails.items.noInternals': 'No internals.',
      'guardrails.items.directional': 'Directional evidence only.',
      'guardrails.items.conditionsChange': 'Conditions can change quickly.',
      'links.eyebrow': 'NEXT SURFACES',
      'links.network': 'Open full network map',
      'links.guide': 'Read the DPI bypass guide',
      'reasonCodes.public_dpi_not_enabled': 'Awaiting sufficient fresh probe signal',
    };

    if (key === 'lastUpdated') {
      return `Last updated ${values?.value ?? ''}`;
    }
    if (key === 'windowValue') {
      return `${values?.hours ?? ''}h window`;
    }

    return dictionary[key] ?? key;
  },
}));

vi.mock('@/lib/api', () => ({
  publicNetworkApi: {
    getDpiScore: getDpiScoreMock,
  },
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({ children, href, ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { children?: ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
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

describe('DpiResistanceDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the truthful gated DPI state from the dedicated endpoint', async () => {
    getDpiScoreMock.mockResolvedValue({
      data: {
        schemaVersion: 'public-network-dpi-score.v1',
        generatedAt: '2026-04-22T12:00:00Z',
        expiresAt: '2026-04-22T12:01:00Z',
        freshnessStatus: 'fresh',
        methodologyVersion: 'dpi-score.methodology.v3.reachability-baseline',
        measurementWindow: {
          hours: 24,
          minimumProbeCount: 12,
        },
        enabled: false,
        confidence: 'low',
        lastUpdatedAt: null,
        reasonCode: 'public_dpi_not_enabled',
        countriesTracked: 18,
        countries: [],
      },
    });

    render(<DpiResistanceDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('LOW')).toBeInTheDocument();
    });

    expect(getDpiScoreMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText('dpi-score.methodology.v3.reachability-baseline')).toBeInTheDocument();
    expect(screen.getByText('HTTPS/SNI application baseline.')).toBeInTheDocument();
    expect(screen.getByText('18')).toBeInTheDocument();
    expect(screen.getByText('24h window')).toBeInTheDocument();
    expect(screen.getByText('Awaiting sufficient fresh probe signal')).toBeInTheDocument();
  });

  it('renders published country scores when the public DPI score is enabled', async () => {
    getDpiScoreMock.mockResolvedValue({
      data: {
        schemaVersion: 'public-network-dpi-score.v1',
        generatedAt: '2026-04-22T12:00:00Z',
        expiresAt: '2026-04-22T12:01:00Z',
        freshnessStatus: 'fresh',
        methodologyVersion: 'dpi-score.methodology.v3.reachability-baseline',
        measurementWindow: {
          hours: 24,
          minimumProbeCount: 12,
        },
        enabled: true,
        confidence: 'medium',
        lastUpdatedAt: '2026-04-22T12:00:00Z',
        reasonCode: null,
        countriesTracked: 2,
        countries: [
          {
            countryCode: 'de',
            publicName: 'DE',
            score: 92,
            confidence: 'high',
            lastUpdatedAt: '2026-04-22T12:00:00Z',
            protocols: [
              {
                protocol: 'vless-tls-ws-tls',
                successRate: 100,
                httpsBaselineSuccessRate: 100,
                medianHandshakeMs: 120,
                medianHttpsBaselineMs: 180,
                lastProbeAt: '2026-04-22T12:00:00Z',
              },
            ],
          },
          {
            countryCode: 'us',
            publicName: 'US',
            score: 88,
            confidence: 'medium',
            lastUpdatedAt: '2026-04-22T12:00:00Z',
            protocols: [
              {
                protocol: 'vless-tls-ws-tls',
                successRate: 95,
                httpsBaselineSuccessRate: 90,
                medianHandshakeMs: 160,
                medianHttpsBaselineMs: 220,
                lastProbeAt: '2026-04-22T12:00:00Z',
              },
            ],
          },
        ],
      },
    });

    render(<DpiResistanceDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Published country scores')).toBeInTheDocument();
    });

    expect(screen.getByText('enabled')).toBeInTheDocument();
    expect(screen.getByText('DE')).toBeInTheDocument();
    expect(screen.getByText('US')).toBeInTheDocument();
    expect(screen.getAllByText('Connect 100%')[0]).toBeInTheDocument();
    expect(screen.getByText('Baseline 100%')).toBeInTheDocument();
    expect(screen.getByText('Handshake 120ms')).toBeInTheDocument();
  });
});
