import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const {
  getConfigMock,
  getDpiScoreMock,
  getProfileMock,
  getServerStatsMock,
  getServersMock,
  getServiceStateMock,
  openMock,
  createObjectURLMock,
  revokeObjectURLMock,
  writeTextMock,
} = vi.hoisted(() => ({
  getConfigMock: vi.fn(),
  getDpiScoreMock: vi.fn(),
  getProfileMock: vi.fn(),
  getServerStatsMock: vi.fn(),
  getServersMock: vi.fn(),
  getServiceStateMock: vi.fn(),
  openMock: vi.fn(),
  createObjectURLMock: vi.fn(),
  revokeObjectURLMock: vi.fn(),
  writeTextMock: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations:
    () =>
    (key: string, values?: Record<string, string | number>) => {
      if (!values) {
        return key;
      }

      return `${key} ${Object.values(values).join(' ')}`;
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

vi.mock('@/lib/api', () => ({
  profileApi: {
    getProfile: getProfileMock,
  },
  publicNetworkApi: {
    getDpiScore: getDpiScoreMock,
  },
  serversApi: {
    getStats: getServerStatsMock,
    list: getServersMock,
  },
  serviceAccessApi: {
    getCurrentServiceState: getServiceStateMock,
  },
  subscriptionsApi: {
    getConfig: getConfigMock,
  },
}));

vi.mock('next/dynamic', () => ({
  default: () => function MockQrCode() {
    return <div data-testid="mock-qr-code" />;
  },
}));

import { ServerAccessDashboard } from '../server-access-dashboard';

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

function mockSuccessfulResponses() {
  getProfileMock.mockResolvedValue({
    data: {
      avatar_url: null,
      display_name: 'Alice',
      email: 'alice@example.com',
      id: 'user-1',
      language: 'en',
      timezone: 'UTC',
    },
  });
  getServersMock.mockResolvedValue({
    data: [
      {
        active_plugin_uuid: null,
        address: '10.0.0.1',
        country_code: 'DE',
        created_at: '2026-04-24T00:00:00Z',
        inbound_count: 2,
        is_connected: true,
        is_disabled: false,
        name: 'Berlin Gateway',
        node_version: '2.3.0',
        port: 443,
        status: 'online',
        traffic_used_bytes: 2048,
        updated_at: '2026-04-24T01:00:00Z',
        users_online: 10,
        uuid: 'server-1',
        vpn_protocol: 'vless',
        xray_version: '1.8.0',
      },
      {
        active_plugin_uuid: null,
        address: '10.0.0.2',
        country_code: 'JP',
        created_at: '2026-04-24T00:00:00Z',
        inbound_count: 1,
        is_connected: false,
        is_disabled: false,
        name: 'Tokyo Reserve',
        node_version: null,
        port: 443,
        status: 'maintenance',
        traffic_used_bytes: 4096,
        updated_at: '2026-04-24T01:00:00Z',
        users_online: 4,
        uuid: 'server-2',
        vpn_protocol: 'wireguard',
        xray_version: null,
      },
    ],
  });
  getServerStatsMock.mockResolvedValue({
    data: {
      maintenance: 1,
      offline: 0,
      online: 1,
      total: 2,
      warning: 0,
    },
  });
  getServiceStateMock.mockResolvedValue({
    data: {
      access_delivery_channel: {
        channel_status: 'active',
      },
      device_credential: {
        credential_status: 'active',
      },
      provisioning_profile: {
        profile_key: 'default',
      },
      service_identity: {
        identity_status: 'active',
      },
    },
  });
  getConfigMock.mockResolvedValue({
    data: {
      config: 'vless://raw-config-value-for-user-1',
      isFound: true,
      links: ['vless://connection-link'],
      ssConfLinks: {},
      subscriptionUrl: 'https://vpn.example/sub/user-1',
    },
  });
  getDpiScoreMock.mockResolvedValue({
    data: {
      confidence: 'high',
      countries: [],
      countriesTracked: 12,
      enabled: true,
      expiresAt: '2026-04-24T02:00:00Z',
      freshnessStatus: 'fresh',
      generatedAt: '2026-04-24T01:00:00Z',
      methodologyVersion: 'dpi-score.v3',
      measurementWindow: {
        hours: 24,
        minimumProbeCount: 10,
      },
      schemaVersion: 'public-network-dpi-score.v1',
    },
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  createObjectURLMock.mockReturnValue('blob:cybervpn-config');
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: createObjectURLMock,
  });
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: revokeObjectURLMock,
  });
  Object.defineProperty(window, 'open', {
    configurable: true,
    value: openMock,
  });
  writeTextMock.mockResolvedValue(undefined);
  vi.stubGlobal('navigator', {
    clipboard: {
      writeText: writeTextMock,
    },
    onLine: true,
  });
  mockSuccessfulResponses();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('ServerAccessDashboard', () => {
  it('renders customer-safe server access and config import actions', async () => {
    renderWithQueryClient(<ServerAccessDashboard />);

    expect(await screen.findAllByText('Berlin Gateway')).toHaveLength(2);
    await waitFor(() => {
      expect(screen.getAllByText('config.status.ready').length).toBeGreaterThan(0);
    });
    expect(screen.getByRole('button', { name: /config\.copySubscription/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /config\.copyConfig/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /config\.downloadConfig/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /config\.openSubscription/i })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /config\.qrCode/i })).toBeInTheDocument();
    expect(screen.getByTestId('mock-qr-code')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /restart/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /stop/i })).not.toBeInTheDocument();
    expect(screen.queryByText('labels.load')).not.toBeInTheDocument();
    expect(screen.queryByText('labels.onlineUsers')).not.toBeInTheDocument();
    expect(screen.queryByText('labels.traffic')).not.toBeInTheDocument();
    expect(screen.queryByText('labels.inbounds')).not.toBeInTheDocument();
    expect(screen.queryByText('labels.nodeVersion')).not.toBeInTheDocument();
    expect(getServerStatsMock).not.toHaveBeenCalled();

    await waitFor(() => {
      expect(getConfigMock).toHaveBeenCalledWith('user-1');
    });
  });

  it('copies, opens, and downloads delivery values without rendering the full secret', async () => {
    const { container } = renderWithQueryClient(<ServerAccessDashboard />);

    fireEvent.click(await screen.findByRole('button', { name: /config\.copySubscription/i }));
    await waitFor(() => {
      expect(writeTextMock).toHaveBeenCalledWith('https://vpn.example/sub/user-1');
    });
    expect(await screen.findByText('copy.subscription')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /config\.copyConfig/i }));
    await waitFor(() => {
      expect(writeTextMock).toHaveBeenCalledWith('vless://raw-config-value-for-user-1');
    });
    expect(screen.queryByText('vless://raw-config-value-for-user-1')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /config\.openSubscription/i }));
    expect(openMock).toHaveBeenCalledWith(
      'https://vpn.example/sub/user-1',
      '_blank',
      'noopener,noreferrer',
    );

    fireEvent.click(screen.getByRole('button', { name: /config\.downloadConfig/i }));
    await waitFor(() => {
      expect(createObjectURLMock).toHaveBeenCalledWith(expect.any(Blob));
    });
    await expect(createObjectURLMock.mock.calls[0][0].text()).resolves.toBe(
      'vless://raw-config-value-for-user-1\n',
    );
    expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:cybervpn-config');
    expect(await screen.findByText('copy.download')).toBeInTheDocument();

    expect(container.textContent).not.toContain('https://vpn.example/sub/user-1');
    expect(container.textContent).not.toContain('vless://raw-config-value-for-user-1');
  });

  it('shows plan and settings recovery links when provisioning is incomplete', async () => {
    getServiceStateMock.mockResolvedValueOnce({
      data: {
        access_delivery_channel: null,
        device_credential: null,
        provisioning_profile: null,
        service_identity: null,
      },
    });

    renderWithQueryClient(<ServerAccessDashboard />);

    expect(await screen.findByText('config.empty.missing_service')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /actions\.managePlan/i })).toHaveAttribute(
      'href',
      '/subscriptions',
    );
    expect(screen.getByRole('link', { name: /actions\.openSettings/i })).toHaveAttribute(
      'href',
      '/settings',
    );
  });
});
