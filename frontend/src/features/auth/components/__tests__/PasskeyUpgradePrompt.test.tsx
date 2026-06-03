import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PasskeyUpgradePrompt } from '../PasskeyUpgradePrompt';

const passkeyMocks = vi.hoisted(() => ({
  getPolicy: vi.fn(),
  listPasskeys: vi.fn(),
  registerPasskey: vi.fn(),
}));

const messages: Record<string, string> = {
  dismissUpgrade: 'Dismiss passkey upgrade prompt',
  upgradeAction: 'Add passkey',
  upgradeAdding: 'Adding...',
  upgradeAriaLabel: 'Passkey upgrade prompt',
  upgradeDescription: 'Add a passkey now.',
  upgradeError: 'Passkey setup did not complete.',
  upgradeSecondary: 'Review settings',
  upgradeTitle: 'Protect this account with a passkey',
};

const passkeyPolicy = {
  enabled: true,
  surface: 'frontend',
  realm_key: 'customer',
  rp_id: 'localhost',
  rp_name: 'CyberVPN',
  allowedOrigins: ['http://localhost:3000'],
  conditionalUiEnabled: true,
  registrationEnabled: true,
  authenticationEnabled: true,
  reauthenticationEnabled: true,
  adminCountsAsMfa: false,
  challengeTtlSeconds: 120,
  browserTimeoutMs: 60000,
};

const credential = {
  id: 'b0f5fbd4-ec5b-46f3-b0cb-1354cfd2d5ab',
  label: 'Work laptop',
  status: 'active',
  credentialType: 'public-key',
  deviceType: 'multiDevice',
  transports: ['internal'],
  backedUp: true,
  userVerified: true,
  createdAt: '2026-06-03T09:00:00Z',
  lastUsedAt: null,
  revokedAt: null,
};

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => messages[key] ?? key,
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...props
  }: Record<string, unknown> & { href?: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('@/lib/api', () => ({
  passkeysApi: {
    getPolicy: passkeyMocks.getPolicy,
    list: passkeyMocks.listPasskeys,
  },
}));

vi.mock('@/features/auth/lib/passkey-webauthn', () => ({
  completePasskeyRegistration: passkeyMocks.registerPasskey,
}));

function renderWithQueryClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <PasskeyUpgradePrompt />
    </QueryClientProvider>,
  );
}

describe('PasskeyUpgradePrompt', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    passkeyMocks.getPolicy.mockResolvedValue({ data: passkeyPolicy });
    passkeyMocks.listPasskeys.mockResolvedValue({ data: { credentials: [] } });
    passkeyMocks.registerPasskey.mockResolvedValue({ data: credential });
  });

  it('offers a post-login passkey upgrade and hides after successful registration', async () => {
    const user = userEvent.setup();
    renderWithQueryClient();

    expect(await screen.findByText('Protect this account with a passkey')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Add passkey' }));

    await waitFor(() => {
      expect(passkeyMocks.registerPasskey).toHaveBeenCalledWith(null);
      expect(screen.queryByText('Protect this account with a passkey')).not.toBeInTheDocument();
    });
  });

  it('stays hidden when the account already has a passkey', async () => {
    passkeyMocks.listPasskeys.mockResolvedValueOnce({
      data: { credentials: [credential] },
    });

    renderWithQueryClient();

    await waitFor(() => expect(passkeyMocks.listPasskeys).toHaveBeenCalled());
    expect(screen.queryByText('Protect this account with a passkey')).not.toBeInTheDocument();
  });

  it('stores a cooldown when dismissed', async () => {
    const user = userEvent.setup();
    renderWithQueryClient();

    expect(await screen.findByText('Protect this account with a passkey')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Dismiss passkey upgrade prompt' }));

    const dismissedUntil = Number(
      window.localStorage.getItem('cybervpn.passkeyUpgrade.dismissedUntil'),
    );

    expect(dismissedUntil).toBeGreaterThan(Date.now());
    expect(screen.queryByText('Protect this account with a passkey')).not.toBeInTheDocument();
  });
});
