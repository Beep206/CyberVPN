import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ConnectionBootstrapPanel } from '../ConnectionBootstrapPanel';

const { apiMocks, clipboardWriteTextMock, routerReplaceMock, windowOpenMock } = vi.hoisted(() => ({
  apiMocks: {
    connectionBootstrap: vi.fn(),
    markConnected: vi.fn(),
  },
  clipboardWriteTextMock: vi.fn(),
  routerReplaceMock: vi.fn(),
  windowOpenMock: vi.fn(),
}));

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api');
  return {
    ...actual,
    customerOnboardingApi: {
      ...actual.customerOnboardingApi,
      connectionBootstrap: apiMocks.connectionBootstrap,
      markConnected: apiMocks.markConnected,
    },
  };
});

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({
    replace: routerReplaceMock,
  }),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    const labels: Record<string, string> = {
      'connection.connected': 'I connected',
      'connection.copyFailed': 'Copy failed',
      'connection.copyHint': 'Copy or open the config link.',
      'connection.copyLink': 'Copy link',
      'connection.copyStepValue': 'Copy value',
      'connection.copySuccess': 'Copied',
      'connection.deviceLimit': `${String(values?.count ?? '')} devices`,
      'connection.expiresAt': `Expires ${String(values?.date ?? '')}`,
      'connection.goDashboard': 'Go to dashboard',
      'connection.goMiniAppHome': 'Go to Mini App home',
      'connection.loading': 'Loading connection details',
      'connection.markConnectedFailed': 'Could not mark connected',
      'connection.networkError': 'Connection bootstrap failed',
      'connection.openLink': 'Open link',
      'connection.pending': 'VPN identity is being prepared.',
      'connection.pendingTitle': 'Preparing VPN',
      'connection.platformTabsLabel': 'Connection platforms',
      'connection.profileName': `Profile ${String(values?.profile ?? '')}`,
      'connection.qrCaption': 'Scan QR',
      'connection.retry': 'Retry',
      'connection.subscriptionUrlLabel': 'Subscription URL',
      'connection.trafficLimit': `Traffic ${String(values?.limit ?? '')}`,
      'connection.unavailable': 'Connection details are unavailable.',
      'connection.unavailableTitle': 'Unavailable',
      'connection.platforms.android': 'Android',
      'connection.platforms.ios': 'iOS',
      'connection.platforms.linux': 'Linux',
      'connection.platforms.macos': 'macOS',
      'connection.platforms.windows': 'Windows',
    };
    return labels[key] ?? key;
  },
}));

vi.mock('react-qr-code', () => ({
  default: ({ value }: { value: string }) => <svg data-testid="qr-code" data-value={value} />,
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function renderPanel(surface: 'web' | 'miniapp' = 'web') {
  return render(<ConnectionBootstrapPanel surface={surface} />, {
    wrapper: createWrapper(),
  });
}

function availableBootstrap(overrides: Record<string, unknown> = {}) {
  return {
    available: true,
    status: 'available',
    message_key: 'Auth.onboarding.connection.available',
    subscription_url: 'https://config.example.invalid/subscription/sample-token',
    qr_payload: 'https://config.example.invalid/subscription/sample-token',
    config_profile_name: 'premium',
    connection_session_id: '11111111-2222-4333-8444-555555555555',
    expires_at: '2026-07-27T00:00:00+00:00',
    flow_key: 'post_registration_growth_code_v1',
    device_limit: 5,
    traffic_limit_bytes: 1_073_741_824,
    instructions: [
      {
        platform: 'ios',
        title_key: 'Auth.onboarding.connection.platforms.ios',
        steps: [
          {
            order: 1,
            title_key: 'Auth.onboarding.connection.instructions.ios.step1.title',
            body_key: 'Auth.onboarding.connection.instructions.ios.step1.body',
            copy_value: 'ios-copy-value',
          },
        ],
        recommended_apps: [{ name: 'CyberVPN iOS', url: 'https://apps.example.invalid/ios' }],
      },
      {
        platform: 'android',
        title_key: 'Auth.onboarding.connection.platforms.android',
        steps: [
          {
            order: 1,
            title_key: 'Auth.onboarding.connection.instructions.android.step1.title',
            body_key: 'Auth.onboarding.connection.instructions.android.step1.body',
          },
        ],
        recommended_apps: [],
      },
    ],
    surface: 'miniapp',
    preferred_layout: 'mobile_panel',
    version: 1,
    supported_actions: [
      'copy_subscription_url',
      'open_subscription_url',
      'show_qr',
      'show_instructions',
      'mark_connected',
      'open_miniapp',
    ],
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function installBrowserMocks() {
  Object.defineProperty(window.navigator, 'userAgent', {
    configurable: true,
    value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)',
  });
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: clipboardWriteTextMock },
  });
  Object.defineProperty(window.navigator, 'clipboard', {
    configurable: true,
    value: { writeText: clipboardWriteTextMock },
  });
  Object.defineProperty(window, 'open', {
    configurable: true,
    value: windowOpenMock,
  });
}

describe('ConnectionBootstrapPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    installBrowserMocks();
    clipboardWriteTextMock.mockResolvedValue(undefined);
    apiMocks.connectionBootstrap.mockResolvedValue({ data: availableBootstrap() });
    apiMocks.markConnected.mockResolvedValue({
      data: {
        status: 'recorded',
        next_destination: '/dashboard',
      },
    });
  });

  it('renders QR and link, supports copy/open, switches platform, and marks Mini App connection', async () => {
    const user = userEvent.setup({ writeToClipboard: false });

    renderPanel('miniapp');

    const subscriptionInput = await screen.findByLabelText('Subscription URL');
    expect(subscriptionInput).toHaveValue('https://config.example.invalid/subscription/sample-token');
    expect(screen.getByTestId('qr-code')).toHaveAttribute(
      'data-value',
      'https://config.example.invalid/subscription/sample-token',
    );
    expect(apiMocks.connectionBootstrap).toHaveBeenCalledWith({
      surface: 'miniapp',
      platform_hint: 'ios',
    });

    installBrowserMocks();
    fireEvent.click(screen.getByRole('button', { name: 'Copy link' }));
    expect(clipboardWriteTextMock).toHaveBeenCalledWith(
      'https://config.example.invalid/subscription/sample-token',
    );
    expect(await screen.findByText('Copied')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Open link' }));
    expect(windowOpenMock).toHaveBeenCalledWith(
      'https://config.example.invalid/subscription/sample-token',
      '_blank',
      'noopener,noreferrer',
    );

    await user.click(screen.getByRole('tab', { name: 'Android' }));
    await waitFor(() => {
      expect(apiMocks.connectionBootstrap).toHaveBeenLastCalledWith({
        surface: 'miniapp',
        platform_hint: 'android',
      });
    });

    await user.click(screen.getByRole('button', { name: 'I connected' }));
    await waitFor(() => {
      expect(apiMocks.markConnected).toHaveBeenCalledWith({
        connection_session_id: '11111111-2222-4333-8444-555555555555',
        flow_key: 'post_registration_growth_code_v1',
        platform: 'android',
        source_surface: 'miniapp',
        version: 1,
      });
    });
    await waitFor(() => {
      expect(routerReplaceMock).toHaveBeenCalledWith('/miniapp/home');
    });
  });

  it('keeps pending bootstrap fail-closed with retry and Mini App fallback navigation', async () => {
    const user = userEvent.setup();
    apiMocks.connectionBootstrap.mockResolvedValue({
      data: availableBootstrap({
        available: false,
        status: 'service_identity_pending',
        subscription_url: null,
        qr_payload: null,
        instructions: [],
      }),
    });

    renderPanel('miniapp');

    expect(await screen.findByText('Preparing VPN')).toBeInTheDocument();
    expect(screen.getByText('VPN identity is being prepared.')).toBeInTheDocument();
    expect(screen.queryByLabelText('Subscription URL')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Retry' }));
    await waitFor(() => {
      expect(apiMocks.connectionBootstrap).toHaveBeenCalledTimes(2);
    });

    await user.click(screen.getByRole('button', { name: 'Go to Mini App home' }));
    expect(routerReplaceMock).toHaveBeenCalledWith('/miniapp/home');
  });

  it('does not expose mark-connected action when bootstrap has no connection session id', async () => {
    apiMocks.connectionBootstrap.mockResolvedValue({
      data: availableBootstrap({
        connection_session_id: null,
      }),
    });

    renderPanel('miniapp');

    expect(await screen.findByText('Unavailable')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'I connected' })).not.toBeInTheDocument();
    expect(apiMocks.markConnected).not.toHaveBeenCalled();
  });

  it('keeps the last QR and subscription URL visible while platform tab refetches', async () => {
    const user = userEvent.setup();
    const androidBootstrap = deferred<{ data: ReturnType<typeof availableBootstrap> }>();
    apiMocks.connectionBootstrap
      .mockResolvedValueOnce({
        data: availableBootstrap({
          subscription_url: 'https://config.example.invalid/subscription/ios-token',
          qr_payload: 'https://config.example.invalid/subscription/ios-token',
        }),
      })
      .mockReturnValueOnce(androidBootstrap.promise);

    renderPanel('miniapp');

    const subscriptionInput = await screen.findByLabelText('Subscription URL');
    expect(subscriptionInput).toHaveValue('https://config.example.invalid/subscription/ios-token');
    expect(screen.getByTestId('qr-code')).toHaveAttribute(
      'data-value',
      'https://config.example.invalid/subscription/ios-token',
    );

    await user.click(screen.getByRole('tab', { name: 'Android' }));

    expect(apiMocks.connectionBootstrap).toHaveBeenLastCalledWith({
      surface: 'miniapp',
      platform_hint: 'android',
    });
    expect(screen.getByLabelText('Subscription URL')).toHaveValue(
      'https://config.example.invalid/subscription/ios-token',
    );
    expect(screen.getByTestId('qr-code')).toHaveAttribute(
      'data-value',
      'https://config.example.invalid/subscription/ios-token',
    );

    androidBootstrap.resolve({
      data: availableBootstrap({
        subscription_url: 'https://config.example.invalid/subscription/android-token',
        qr_payload: 'https://config.example.invalid/subscription/android-token',
      }),
    });

    await waitFor(() => {
      expect(screen.getByLabelText('Subscription URL')).toHaveValue(
        'https://config.example.invalid/subscription/android-token',
      );
    });
    expect(screen.getByTestId('qr-code')).toHaveAttribute(
      'data-value',
      'https://config.example.invalid/subscription/android-token',
    );
  });
});
