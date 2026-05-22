import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { VpnConfigCard } from '../VpnConfigCard';

const apiMocks = vi.hoisted(() => ({
  miniappApi: {
    getConfig: vi.fn(),
  },
}));

const runtimeAnalyticsMocks = vi.hoisted(() => ({
  emitMiniAppRuntimeEvent: vi.fn().mockResolvedValue(undefined),
}));

const telegramMocks = vi.hoisted(() => ({
  showAlert: vi.fn(),
  openLink: vi.fn(),
  haptic: vi.fn(),
}));

vi.mock('@/lib/api', () => apiMocks);

vi.mock('../../hooks/useTelegramWebApp', () => ({
  useTelegramWebApp: () => ({
    haptic: telegramMocks.haptic,
    webApp: {
      showAlert: telegramMocks.showAlert,
      openLink: telegramMocks.openLink,
    },
  }),
}));

vi.mock('@/features/miniapp-runtime/lib/runtime-analytics', () => runtimeAnalyticsMocks);

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string) => key,
}));

vi.mock('next/dynamic', () => ({
  default: () => function MockQrCode() {
    return <div data-testid="mock-qr-code" />;
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('VpnConfigCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  it('emits config_loaded for generated Mini App configs', async () => {
    apiMocks.miniappApi.getConfig.mockResolvedValue({
      data: {
        config: 'vless://generated',
        configString: 'vless://generated',
        clientType: 'vless',
        source: 'remnawave_generated',
        isFound: true,
        links: ['vless://generated'],
        ssConfLinks: {},
        subscriptionUrl: 'https://example.com/sub',
        generatedAt: '2026-04-22T12:00:00Z',
      },
    });

    render(<VpnConfigCard colorScheme="dark" page="profile" />, { wrapper: createWrapper() });

    await screen.findByText('vpnConfigTitle');
    await waitFor(() => {
      expect(runtimeAnalyticsMocks.emitMiniAppRuntimeEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          event: 'miniapp_config_loaded',
          page: 'profile',
          locale: 'en-EN',
          path: '/en-EN/miniapp/profile',
          configSource: 'remnawave_generated',
        }),
      );
    });
  });

  it('uses the subscription URL for copy and app-open actions when direct links are present', async () => {
    apiMocks.miniappApi.getConfig.mockResolvedValue({
      data: {
        config: 'vless://generated-direct-link',
        configString: 'vless://generated-direct-link',
        clientType: 'vless',
        source: 'remnawave_generated',
        isFound: true,
        links: ['vless://generated-direct-link'],
        ssConfLinks: {},
        subscriptionUrl: 'https://cyber-vpn.org/api/sub/redacted',
        generatedAt: '2026-04-22T12:00:00Z',
      },
    });

    render(<VpnConfigCard colorScheme="dark" page="home" />, { wrapper: createWrapper() });

    await screen.findByText('vpnConfigTitle');
    fireEvent.click(screen.getByText('copyConfig'));
    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('https://cyber-vpn.org/api/sub/redacted');
    });

    fireEvent.click(screen.getByText('openInApp'));
    expect(telegramMocks.openLink).toHaveBeenCalledWith('https://cyber-vpn.org/api/sub/redacted');
  });

  it('emits config_failed when config fetch fails', async () => {
    apiMocks.miniappApi.getConfig.mockRejectedValue({
      response: {
        data: {
          detail: 'Config delivery is temporarily unavailable.',
        },
      },
    });

    render(<VpnConfigCard colorScheme="dark" page="home" />, { wrapper: createWrapper() });

    await screen.findByText('noConfigAvailable');
    expect(screen.getByText('Config delivery is temporarily unavailable.')).toBeInTheDocument();
    await waitFor(() => {
      expect(runtimeAnalyticsMocks.emitMiniAppRuntimeEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          event: 'miniapp_config_failed',
          page: 'home',
          locale: 'en-EN',
          path: '/en-EN/miniapp/home',
          errorCode: 'config_fetch_failed',
        }),
      );
    });
  });
});
