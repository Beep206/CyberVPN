import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SettingsCabinetDashboard } from '../settings-cabinet-dashboard';

const setupUser = () => userEvent.setup({ writeToClipboard: false });

const apiMocks = vi.hoisted(() => ({
  authMe: vi.fn(),
  clipboardWriteText: vi.fn(),
  getAntiphishingCode: vi.fn(),
  getCurrentEntitlement: vi.fn(),
  getGrowthPreferences: vi.fn(),
  getNotificationPreferences: vi.fn(),
  getPasskeyPolicy: vi.fn(),
  getProfile: vi.fn(),
  getTwoFactorStatus: vi.fn(),
  listDevices: vi.fn(),
  listPasskeys: vi.fn(),
  logoutDevice: vi.fn(),
  logoutOtherDevices: vi.fn(),
  mapPasskeyErrorMessageKey: vi.fn(),
  markPerformance: vi.fn(),
  registerPasskey: vi.fn(),
  requestTelegramAccountLink: vi.fn(),
  requestPasskeyFreshAuthGrant: vi.fn(),
  renamePasskey: vi.fn(),
  pollTelegramAccountLinkStatus: vi.fn(),
  deletePasskey: vi.fn(),
  updateGrowthPreferences: vi.fn(),
  updateNotificationPreferences: vi.fn(),
  updateProfile: vi.fn(),
}));

function installClipboardMock() {
  const clipboard = navigator.clipboard ?? {
    writeText: apiMocks.clipboardWriteText,
  };
  Object.defineProperty(clipboard, 'writeText', {
    configurable: true,
    value: apiMocks.clipboardWriteText,
  });
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: clipboard,
  });
  Object.defineProperty(window.navigator, 'clipboard', {
    configurable: true,
    value: clipboard,
  });
}

function setupUserWithMockedClipboard() {
  const user = setupUser();
  installClipboardMock();
  return user;
}

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string, params?: Record<string, unknown>) =>
    params ? `${key} ${JSON.stringify(params)}` : key,
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('@/shared/lib/web-vitals', () => ({
  markPerformance: apiMocks.markPerformance,
}));

vi.mock('@/features/auth/lib/passkey-webauthn', () => ({
  completePasskeyRegistration: apiMocks.registerPasskey,
  getPasskeyErrorMessageKey: apiMocks.mapPasskeyErrorMessageKey,
}));

vi.mock('@/features/auth/lib/passkey-fresh-auth', () => ({
  requestPasskeyFreshAuthGrant: apiMocks.requestPasskeyFreshAuthGrant,
}));

vi.mock('@/app/[locale]/(dashboard)/settings/components/TwoFactorModal', () => ({
  TwoFactorModal: ({
    isOpen,
    onSuccess,
  }: {
    isOpen: boolean;
    onSuccess: () => void;
  }) => (isOpen ? <button onClick={onSuccess}>mock-two-factor-modal</button> : null),
}));

vi.mock('@/app/[locale]/(dashboard)/settings/components/ChangePasswordModal', () => ({
  ChangePasswordModal: ({
    isOpen,
    onSuccess,
  }: {
    isOpen: boolean;
    onSuccess: () => void;
  }) => (isOpen ? <button onClick={onSuccess}>mock-password-modal</button> : null),
}));

vi.mock('@/app/[locale]/(dashboard)/settings/components/AntiphishingModal', () => ({
  AntiphishingModal: ({
    isOpen,
    onSuccess,
  }: {
    isOpen: boolean;
    onSuccess: () => void;
  }) => (isOpen ? <button onClick={onSuccess}>mock-antiphishing-modal</button> : null),
}));

vi.mock('@/lib/api', () => ({
  authApi: {
    listDevices: apiMocks.listDevices,
    logoutDevice: apiMocks.logoutDevice,
    logoutOtherDevices: apiMocks.logoutOtherDevices,
    me: apiMocks.authMe,
    pollTelegramAccountLinkStatus: apiMocks.pollTelegramAccountLinkStatus,
    requestTelegramAccountLink: apiMocks.requestTelegramAccountLink,
  },
  entitlementsApi: {
    getCurrent: apiMocks.getCurrentEntitlement,
  },
  growthNotificationsApi: {
    getPreferences: apiMocks.getGrowthPreferences,
    updatePreferences: apiMocks.updateGrowthPreferences,
  },
  passkeysApi: {
    delete: apiMocks.deletePasskey,
    getPolicy: apiMocks.getPasskeyPolicy,
    list: apiMocks.listPasskeys,
    rename: apiMocks.renamePasskey,
  },
  profileApi: {
    getNotificationPreferences: apiMocks.getNotificationPreferences,
    getProfile: apiMocks.getProfile,
    updateNotificationPreferences: apiMocks.updateNotificationPreferences,
    updateProfile: apiMocks.updateProfile,
  },
  securityApi: {
    getAntiphishingCode: apiMocks.getAntiphishingCode,
  },
  twofaApi: {
    getStatus: apiMocks.getTwoFactorStatus,
  },
}));

function renderDashboard(view: 'overview' | 'security' = 'overview') {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <SettingsCabinetDashboard view={view} />
    </QueryClientProvider>,
  );
}

const profile = {
  avatar_url: null,
  display_name: 'Cipher Ops',
  email: 'operator@example.com',
  id: '7d871bc5-af6c-49b2-a3e6-e77eec938021',
  language: 'en-EN',
  timezone: 'UTC',
  updated_at: '2026-04-24T10:00:00Z',
};

const corePreferences = {
  email_marketing: false,
  email_security: true,
  push_connection: true,
  push_payment: true,
  push_subscription: true,
};

const growthPreferences = {
  growth_email_admin_updates: true,
  growth_email_gifts: true,
  growth_email_invites: false,
  growth_email_referral_rewards: true,
  growth_in_app_admin_updates: true,
  growth_in_app_gifts: true,
  growth_in_app_invites: true,
  growth_in_app_referral_rewards: true,
  growth_telegram_admin_updates: true,
  growth_telegram_gifts: true,
  growth_telegram_invites: true,
  growth_telegram_referral_rewards: true,
};

const devices = {
  devices: [
    {
      created_at: '2026-04-20T10:00:00Z',
      device_id: 'device-current',
      ip_address: '127.0.0.1',
      is_current: true,
      last_used_at: '2026-04-24T10:00:00Z',
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
    },
    {
      created_at: '2026-04-18T10:00:00Z',
      device_id: 'device-remote',
      ip_address: '10.0.0.2',
      is_current: false,
      last_used_at: '2026-04-23T10:00:00Z',
      user_agent: 'Mozilla/5.0 (iPhone) Mobile Safari/604.1',
    },
  ],
  total: 2,
  total_devices: 2,
  device_limit: 3,
  remaining_devices: 1,
};

const entitlement = {
  addons: [],
  display_name: 'CyberVPN Plus',
  effective_entitlements: {
    device_limit: 3,
  },
  expires_at: '2026-05-24T10:00:00Z',
  invite_bundle: {},
  is_trial: false,
  period_days: 30,
  plan_code: 'plus',
  plan_uuid: 'plan-plus',
  status: 'active',
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

const passkeys = {
  credentials: [
    {
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
    },
  ],
};

describe('SettingsCabinetDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.clipboardWriteText.mockResolvedValue(undefined);
    installClipboardMock();

    apiMocks.getProfile.mockResolvedValue({ data: profile });
    apiMocks.authMe.mockResolvedValue({
      data: {
        created_at: '2026-04-20T10:00:00Z',
        email: 'operator@example.com',
        id: '7d871bc5-af6c-49b2-a3e6-e77eec938021',
        public_uid: 14677650,
        is_active: true,
        is_email_verified: true,
        role: 'user',
        telegram_id: 777,
      },
    });
    apiMocks.getTwoFactorStatus.mockResolvedValue({ data: { status: 'enabled' } });
    apiMocks.getAntiphishingCode.mockResolvedValue({ data: { code: 'CYBER-ALPHA' } });
    apiMocks.getNotificationPreferences.mockResolvedValue({ data: corePreferences });
    apiMocks.getGrowthPreferences.mockResolvedValue({ data: growthPreferences });
    apiMocks.getPasskeyPolicy.mockResolvedValue({ data: passkeyPolicy });
    apiMocks.listPasskeys.mockResolvedValue({ data: passkeys });
    apiMocks.registerPasskey.mockResolvedValue({ data: passkeys.credentials[0] });
    apiMocks.requestPasskeyFreshAuthGrant.mockResolvedValue('fresh-auth-grant');
    apiMocks.mapPasskeyErrorMessageKey.mockReturnValue('passkeyGenericError');
    apiMocks.renamePasskey.mockResolvedValue({
      data: {
        ...passkeys.credentials[0],
        label: 'Phone',
      },
    });
    apiMocks.deletePasskey.mockResolvedValue({
      data: {
        id: passkeys.credentials[0].id,
        status: 'revoked',
      },
    });
    apiMocks.getCurrentEntitlement.mockResolvedValue({ data: entitlement });
    apiMocks.listDevices.mockResolvedValue({ data: devices });
    apiMocks.updateProfile.mockImplementation((payload) => ({
      data: {
        ...profile,
        display_name: payload.display_name,
        language: payload.language,
        timezone: payload.timezone,
      },
    }));
    apiMocks.updateNotificationPreferences.mockImplementation((payload) => ({
      data: {
        ...corePreferences,
        ...payload,
      },
    }));
    apiMocks.updateGrowthPreferences.mockImplementation((payload) => ({
      data: {
        ...growthPreferences,
        ...payload,
      },
    }));
    apiMocks.logoutDevice.mockResolvedValue({ data: { device_id: 'device-remote', message: 'ok' } });
    apiMocks.logoutOtherDevices.mockResolvedValue({
      data: { message: 'Other device sessions terminated', sessions_revoked: 1 },
    });
    apiMocks.requestTelegramAccountLink.mockResolvedValue({
      data: {
        token: 'account_link_token_123',
        bot_url: 'https://t.me/CyberVPNBot?start=link_account_link_token_123',
        deep_link_url: 'tg://resolve?domain=CyberVPNBot&start=link_account_link_token_123',
        expires_in: 300,
      },
    });
    apiMocks.pollTelegramAccountLinkStatus.mockResolvedValue({
      data: {
        status: 'linked',
        provider: 'telegram',
        provider_user_id: '424242',
      },
    });
  });

  it('renders backend profile, language, timezone, notifications, identity, and cabinet links', async () => {
    renderDashboard();

    expect(await screen.findByDisplayValue('operator@example.com')).toBeInTheDocument();
    expect(screen.getByRole('option', { name: '🇺🇸 English' })).toHaveValue('en-EN');
    expect(screen.getByRole('option', { name: 'UTC (UTC+00:00)' })).toHaveValue('UTC');
    expect(screen.getByText('14677650')).toBeInTheDocument();
    expect(screen.queryByText('7d871bc5-af6c-49b2-a3e6-e77eec938021')).not.toBeInTheDocument();
    expect(screen.getByText(/identity.telegramLinked/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'actions.openSecurity' })).toHaveAttribute(
      'href',
      '/settings/security',
    );
    expect(screen.getAllByRole('link', { name: 'actions.deleteAccount' })[0]).toHaveAttribute(
      'href',
      '/settings/delete-account',
    );
    expect(screen.queryByText('security.twoFactor.title')).not.toBeInTheDocument();
    expect(screen.getByText('profile.title').closest('article')?.parentElement).toHaveClass(
      'contents',
    );
    expect(screen.getByText('notifications.title').closest('article')?.parentElement).toHaveClass(
      'contents',
    );
  });

  it('renders sensitive security controls and device state in the security view', async () => {
    renderDashboard('security');

    expect(await screen.findByText('security.twoFactor.title')).toBeInTheDocument();
    expect(await screen.findByText('CY*******HA')).toBeInTheDocument();
    expect(await screen.findByText('Work laptop')).toBeInTheDocument();
    expect(screen.getAllByText(/Chrome \/ Windows NT 10.0/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Safari \/ Unknown OS/)).toBeInTheDocument();
    expect(screen.getByText('summary.devices').closest('article')).toHaveTextContent('2');
    expect(screen.queryByText('devices.limitTitle')).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'devices.managePlan' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'actions.profileSettings' })).toHaveAttribute(
      'href',
      '/settings',
    );
  });

  it('uses backend-owned session totals without VPN entitlement quota fallback', async () => {
    apiMocks.listDevices.mockResolvedValueOnce({
      data: {
        ...devices,
        device_limit: 5,
        remaining_devices: 1,
        total_devices: 4,
      },
    });
    apiMocks.getCurrentEntitlement.mockResolvedValueOnce({
      data: {
        ...entitlement,
        effective_entitlements: {
          device_limit: 9,
        },
      },
    });

    renderDashboard('security');

    await screen.findByText('Work laptop');
    expect(
      screen.getByText('summary.devices').closest('article'),
    ).toHaveTextContent('4');
    expect(screen.queryByText('devices.limitTitle')).not.toBeInTheDocument();
    expect(apiMocks.getCurrentEntitlement).not.toHaveBeenCalled();
  });

  it('renders a single current device badge when duplicate rows are flagged current', async () => {
    apiMocks.listDevices.mockResolvedValueOnce({
      data: {
        ...devices,
        devices: devices.devices.map((device) => ({
          ...device,
          is_current: true,
        })),
      },
    });

    renderDashboard('security');

    expect(await screen.findAllByText('devices.current')).toHaveLength(1);
  });

  it('updates profile fields and records a performance mark', async () => {
    const user = setupUser();
    renderDashboard();

    const displayNameInput = await screen.findByDisplayValue('Cipher Ops');
    await user.clear(displayNameInput);
    await user.type(displayNameInput, 'Cipher Prime');
    await user.click(screen.getByRole('button', { name: 'actions.saveProfile' }));

    await waitFor(() => {
      expect(apiMocks.updateProfile).toHaveBeenCalledWith({
        display_name: 'Cipher Prime',
        language: 'en-EN',
        timezone: 'UTC',
      });
    });
    expect(apiMocks.markPerformance).toHaveBeenCalledWith(
      'settings-profile-save',
      expect.objectContaining({ changed_language: 'en-EN' }),
    );
  });

  it('submits empty profile fields as null and shows failure feedback', async () => {
    const user = setupUser();
    apiMocks.updateProfile.mockRejectedValueOnce(new Error('profile write failed'));

    renderDashboard();

    const displayNameInput = await screen.findByDisplayValue('Cipher Ops');
    await user.clear(displayNameInput);
    await user.selectOptions(screen.getByLabelText('profile.language'), '');
    await user.selectOptions(screen.getByLabelText('profile.timezone'), '');
    await user.click(screen.getByRole('button', { name: 'actions.saveProfile' }));

    await waitFor(() => {
      expect(apiMocks.updateProfile).toHaveBeenCalledWith({
        display_name: null,
        language: null,
        timezone: null,
      });
    });
    expect(await screen.findByText('feedback.profileFailed')).toBeInTheDocument();
  });

  it('refreshes all settings dependencies from the hero action', async () => {
    const user = setupUser();
    renderDashboard();

    await screen.findByDisplayValue('operator@example.com');
    await user.click(screen.getByRole('button', { name: 'actions.refresh' }));

    await waitFor(() => {
      expect(apiMocks.getProfile).toHaveBeenCalledTimes(2);
      expect(apiMocks.authMe).toHaveBeenCalledTimes(2);
      expect(apiMocks.getTwoFactorStatus).toHaveBeenCalledTimes(2);
      expect(apiMocks.getAntiphishingCode).toHaveBeenCalledTimes(2);
      expect(apiMocks.getNotificationPreferences).toHaveBeenCalledTimes(2);
      expect(apiMocks.getGrowthPreferences).toHaveBeenCalledTimes(2);
      expect(apiMocks.getCurrentEntitlement).not.toHaveBeenCalled();
      expect(apiMocks.listDevices).toHaveBeenCalledTimes(2);
    });
  });

  it('updates core and growth notification preferences', async () => {
    const user = setupUser();
    renderDashboard();

    const coreSwitch = await screen.findByRole('switch', {
      name: /notifications\.core\.emailMarketing\.title/,
    });
    const growthSwitch = screen.getByRole('switch', {
      name: /notifications\.growth\.emailRewards\.title/,
    });
    const coreThumb = coreSwitch.querySelector('span span');
    const growthThumb = growthSwitch.querySelector('span span');

    expect(coreSwitch).toHaveAttribute('aria-checked', 'false');
    expect(coreThumb).not.toBeNull();
    expect(coreThumb!).toHaveClass('translate-x-0', 'bg-white');
    expect(growthSwitch).toHaveAttribute('aria-checked', 'true');
    expect(growthThumb).not.toBeNull();
    expect(growthThumb!).toHaveClass('translate-x-5', 'bg-matrix-green');

    await user.click(coreSwitch);
    await user.click(growthSwitch);

    await waitFor(() => {
      expect(apiMocks.updateNotificationPreferences).toHaveBeenCalledWith({
        email_marketing: true,
      });
      expect(apiMocks.updateGrowthPreferences).toHaveBeenCalledWith({
        growth_email_referral_rewards: false,
      });
    });
    expect(apiMocks.markPerformance).toHaveBeenCalledWith(
      'settings-notification-toggle',
      expect.objectContaining({
        channel: 'core',
        enabled: true,
        key: 'email_marketing',
      }),
    );
    expect(apiMocks.markPerformance).toHaveBeenCalledWith(
      'settings-notification-toggle',
      expect.objectContaining({
        channel: 'growth',
        enabled: false,
        key: 'growth_email_referral_rewards',
      }),
    );
  });

  it('shows notification failure feedback when growth preference updates fail', async () => {
    const user = setupUser();
    apiMocks.updateGrowthPreferences.mockRejectedValueOnce(new Error('growth write failed'));

    renderDashboard();

    await screen.findByText('notifications.growth.emailRewards.title');
    await user.click(screen.getByText('notifications.growth.emailRewards.title'));

    expect(await screen.findByText('feedback.notificationsFailed')).toBeInTheDocument();
  });

  it('shows a partial data banner when a settings dependency fails', async () => {
    apiMocks.getGrowthPreferences.mockRejectedValueOnce(new Error('growth preferences unavailable'));

    renderDashboard();

    expect(await screen.findByDisplayValue('operator@example.com')).toBeInTheDocument();
    expect(await screen.findByText('errors.partialTitle')).toBeInTheDocument();
    expect(screen.getByText('errors.partialDescription')).toBeInTheDocument();
  });

  it('shows notification failure feedback when preference updates fail', async () => {
    const user = setupUser();
    apiMocks.updateNotificationPreferences.mockRejectedValueOnce(new Error('notification write failed'));

    renderDashboard();

    await screen.findByText('notifications.core.emailMarketing.title');
    await user.click(screen.getByText('notifications.core.emailMarketing.title'));

    expect(await screen.findByText('feedback.notificationsFailed')).toBeInTheDocument();
  });

  it('revokes a non-current device through the backend API', async () => {
    const user = setupUser();
    const logoutDeferred: { resolve?: () => void } = {};
    apiMocks.logoutDevice.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          logoutDeferred.resolve = resolve;
        }),
    );

    renderDashboard('security');

    const revokeButtons = await screen.findAllByRole('button', {
      name: 'devices.revokeDevice',
    });
    await user.click(revokeButtons[0]);
    expect(screen.getByText('actions.revoking')).toBeInTheDocument();
    expect(logoutDeferred.resolve).toBeDefined();
    logoutDeferred.resolve?.();

    await waitFor(() => {
      expect(apiMocks.logoutDevice).toHaveBeenCalledWith('device-remote');
    });
    expect(apiMocks.markPerformance).toHaveBeenCalledWith(
      'settings-device-revoke',
      expect.objectContaining({ scope: 'single' }),
    );
  });

  it('shows failure feedback when a single device revocation fails', async () => {
    const user = setupUser();
    apiMocks.logoutDevice.mockRejectedValueOnce(new Error('revoke failed'));

    renderDashboard('security');

    const revokeButtons = await screen.findAllByRole('button', {
      name: 'devices.revokeDevice',
    });
    await user.click(revokeButtons[0]);

    expect(await screen.findByText('feedback.deviceFailed')).toBeInTheDocument();
  });

  it('revokes all non-current devices through the backend API', async () => {
    const user = setupUser();
    renderDashboard('security');

    await screen.findByText('Work laptop');
    expect(screen.getByText('devices.otherSessions')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'devices.revokeOthers' }));

    await waitFor(() => {
      expect(apiMocks.logoutOtherDevices).toHaveBeenCalledTimes(1);
    });
    expect(apiMocks.logoutDevice).not.toHaveBeenCalled();
    expect(apiMocks.markPerformance).toHaveBeenCalledWith(
      'settings-device-revoke',
      expect.objectContaining({ count: 1, scope: 'others' }),
    );
    expect(await screen.findByText('feedback.devicesRevoked {"count":1}')).toBeInTheDocument();
  });

  it('shows failure feedback when bulk device revocation fails', async () => {
    const user = setupUser();
    apiMocks.logoutOtherDevices.mockRejectedValueOnce(new Error('bulk revoke failed'));

    renderDashboard('security');

    await screen.findByText('Work laptop');
    expect(screen.getByText('devices.otherSessions')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'devices.revokeOthers' }));

    expect(await screen.findByText('feedback.deviceFailed')).toBeInTheDocument();
  });

  it('renders an empty device state and disables bulk revocation', async () => {
    apiMocks.listDevices.mockResolvedValueOnce({ data: { devices: [], total: 0 } });

    renderDashboard('security');

    expect(await screen.findByText('devices.empty')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'devices.revokeOthers' })).toBeDisabled();
  });

  it('keeps device actions usable without VPN entitlement quota data', async () => {
    apiMocks.listDevices.mockResolvedValueOnce({
      data: {
        ...devices,
        device_limit: null,
        remaining_devices: null,
      },
    });
    renderDashboard('security');

    await screen.findByText('Work laptop');
    expect(screen.getByText('devices.otherSessions')).toBeInTheDocument();
    expect(screen.queryByText('devices.limitTitle')).not.toBeInTheDocument();
    expect(apiMocks.getCurrentEntitlement).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'devices.revokeOthers' })).toBeEnabled();
  });

  it('copies account id and records privacy-safe telemetry', async () => {
    const user = setupUserWithMockedClipboard();
    renderDashboard();

    await screen.findByDisplayValue('operator@example.com');
    await user.click(screen.getByRole('button', { name: 'actions.copyId' }));

    await waitFor(() => {
      expect(apiMocks.clipboardWriteText).toHaveBeenCalledWith('14677650');
    });
    expect(apiMocks.markPerformance).toHaveBeenCalledWith('settings-account-id-copy');
    expect(screen.getByRole('button', { name: 'actions.copied' })).toBeInTheDocument();
  });

  it('resets copied account id state after the feedback timeout', async () => {
    const user = setupUserWithMockedClipboard();
    renderDashboard();

    await screen.findByDisplayValue('operator@example.com');
    await user.click(screen.getByRole('button', { name: 'actions.copyId' }));

    await waitFor(() => {
      expect(apiMocks.clipboardWriteText).toHaveBeenCalledWith('14677650');
    });
    expect(screen.getByRole('button', { name: 'actions.copied' })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'actions.copyId' })).toBeInTheDocument();
    }, { timeout: 2_500 });
  });

  it('shows feedback when account id copy fails', async () => {
    const user = setupUserWithMockedClipboard();
    apiMocks.clipboardWriteText.mockRejectedValueOnce(new Error('clipboard denied'));

    renderDashboard();

    await screen.findByDisplayValue('operator@example.com');
    await user.click(screen.getByRole('button', { name: 'actions.copyId' }));

    expect(await screen.findByText('feedback.copyFailed')).toBeInTheDocument();
  });

  it('starts Telegram account linking with a link deep link and refreshes the current user', async () => {
    const user = setupUser();
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    apiMocks.authMe
      .mockResolvedValueOnce({
        data: {
          created_at: '2026-04-20T10:00:00Z',
          email: 'operator@example.com',
          id: 'user-1',
          is_active: true,
          is_email_verified: true,
          role: 'user',
          telegram_id: null,
        },
      })
      .mockResolvedValue({
        data: {
          created_at: '2026-04-20T10:00:00Z',
          email: 'operator@example.com',
          id: 'user-1',
          is_active: true,
          is_email_verified: true,
          role: 'user',
          telegram_id: 424242,
        },
      });

    renderDashboard();

    expect(await screen.findByText('identity.telegramMissing')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'actions.manage' }));

    await waitFor(() => {
      expect(apiMocks.requestTelegramAccountLink).toHaveBeenCalledTimes(1);
      expect(apiMocks.pollTelegramAccountLinkStatus).toHaveBeenCalledWith('account_link_token_123');
    });
    expect(openSpy).toHaveBeenCalledWith(
      'tg://resolve?domain=CyberVPNBot&start=link_account_link_token_123',
      '_blank',
      'noopener,noreferrer',
    );
    expect(await screen.findByText('feedback.securityUpdated')).toBeInTheDocument();

    openSpy.mockRestore();
  });

  it('renders exposed fallback posture, missing identity, and resilient device metadata', async () => {
    apiMocks.getProfile.mockResolvedValueOnce({
      data: {
        ...profile,
        display_name: null,
        email: null,
        id: null,
        language: null,
        timezone: null,
        updated_at: null,
      },
    });
    apiMocks.authMe.mockResolvedValueOnce({
      data: {
        created_at: '2026-04-20T10:00:00Z',
        email: 'operator@example.com',
        id: '7d871bc5-af6c-49b2-a3e6-e77eec938021',
        public_uid: null,
        is_active: true,
        is_email_verified: false,
        role: 'user',
        telegram_id: null,
      },
    });
    apiMocks.getTwoFactorStatus.mockResolvedValueOnce({ data: { status: 'disabled' } });
    apiMocks.getAntiphishingCode.mockResolvedValueOnce({ data: { code: null } });
    apiMocks.getNotificationPreferences.mockResolvedValueOnce({
      data: {
        email_marketing: false,
        email_security: false,
        push_connection: false,
        push_payment: false,
        push_subscription: false,
      },
    });
    apiMocks.getCurrentEntitlement.mockResolvedValueOnce({
      data: {
        ...entitlement,
        effective_entitlements: {
          device_limit: 2,
        },
      },
    });
    apiMocks.listDevices.mockResolvedValueOnce({
      data: {
        devices: [
          {
            created_at: '2026-04-18T10:00:00Z',
            device_id: 'tablet-remote',
            ip_address: null,
            is_current: false,
            last_used_at: '2026-04-23T10:00:00Z',
            user_agent:
              'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) Version/17.0 Mobile/15E148 Safari/604.1',
          },
          {
            created_at: '2026-04-18T11:00:00Z',
            device_id: 'android-remote',
            ip_address: '10.0.0.3',
            is_current: false,
            last_used_at: '2026-04-23T11:00:00Z',
            user_agent: 'Mozilla/5.0 Android 15 Chrome/124.0.0.0',
          },
          {
            created_at: '2026-04-18T12:00:00Z',
            device_id: 'linux-remote',
            ip_address: '10.0.0.4',
            is_current: false,
            last_used_at: '2026-04-23T12:00:00Z',
            user_agent: 'Mozilla/5.0 Linux Firefox/123.0',
          },
          {
            created_at: '2026-04-18T13:00:00Z',
            device_id: null,
            ip_address: null,
            is_current: false,
            last_used_at: '2026-04-23T13:00:00Z',
            user_agent: '',
          },
        ],
        total: 4,
      },
    });

    renderDashboard();

    expect(await screen.findByDisplayValue('labels.notAvailable')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'actions.copyId' })).toBeDisabled();
    expect(screen.getByText('posture.exposed')).toBeInTheDocument();
    expect(screen.getAllByText('labels.notSet').length).toBeGreaterThan(0);
    expect(screen.getByText('identity.telegramMissing')).toBeInTheDocument();
  });

  it('opens sensitive security flows from the security view', async () => {
    const user = setupUser();
    renderDashboard('security');

    await screen.findByText('security.twoFactor.title');

    await user.click(screen.getByText('security.twoFactor.title'));
    expect(screen.getByText('mock-two-factor-modal')).toBeInTheDocument();
    expect(apiMocks.markPerformance).toHaveBeenCalledWith(
      'settings-security-action-open',
      expect.objectContaining({ modal: 'twoFactor' }),
    );
  });

  it('refetches security status after two factor and antiphishing modal completion', async () => {
    const user = setupUser();
    renderDashboard('security');

    await screen.findByText('security.twoFactor.title');

    await user.click(screen.getByText('security.twoFactor.title'));
    await user.click(screen.getByText('mock-two-factor-modal'));

    await waitFor(() => {
      expect(apiMocks.getTwoFactorStatus).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByText('feedback.securityUpdated')).toBeInTheDocument();

    await user.click(screen.getByText('security.antiphishing.title'));
    await user.click(screen.getByText('mock-antiphishing-modal'));

    await waitFor(() => {
      expect(apiMocks.getAntiphishingCode).toHaveBeenCalledTimes(2);
    });
    expect(apiMocks.markPerformance).toHaveBeenCalledWith(
      'settings-security-action-open',
      expect.objectContaining({ modal: 'antiphishing' }),
    );
  });

  it('shows success feedback after sensitive security modal completion', async () => {
    const user = setupUser();
    renderDashboard('security');

    await screen.findByText('security.password.title');
    await user.click(screen.getByText('security.password.title'));
    await user.click(screen.getByText('mock-password-modal'));

    expect(await screen.findByText('feedback.securityUpdated')).toBeInTheDocument();
  });

  it('reauthenticates before renaming a passkey and sends the fresh-auth grant', async () => {
    const user = setupUser();
    apiMocks.requestPasskeyFreshAuthGrant.mockResolvedValueOnce('fresh-rename-grant');
    renderDashboard('security');

    await screen.findByText('Work laptop');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.renameAction' }));
    const renameInput = screen.getByDisplayValue('Work laptop');
    await user.clear(renameInput);
    await user.type(renameInput, 'Phone');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.saveRename' }));

    await waitFor(() => {
      expect(apiMocks.requestPasskeyFreshAuthGrant).toHaveBeenCalledWith(
        `passkey.credential.rename:${passkeys.credentials[0].id}`,
      );
      expect(apiMocks.renamePasskey).toHaveBeenCalledWith(passkeys.credentials[0].id, 'Phone', {
        freshAuthGrantId: 'fresh-rename-grant',
      });
    });
    expect(apiMocks.requestPasskeyFreshAuthGrant.mock.invocationCallOrder[0]).toBeLessThan(
      apiMocks.renamePasskey.mock.invocationCallOrder[0],
    );
    expect(await screen.findByText('feedback.passkeyRenamed')).toBeInTheDocument();
  });

  it('does not rename a passkey when fresh-auth ceremony is cancelled', async () => {
    const user = setupUser();
    apiMocks.requestPasskeyFreshAuthGrant.mockRejectedValueOnce(
      new DOMException('Cancelled', 'AbortError'),
    );
    apiMocks.mapPasskeyErrorMessageKey.mockReturnValueOnce('passkeyCancelled');
    renderDashboard('security');

    await screen.findByText('Work laptop');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.renameAction' }));
    const renameInput = screen.getByDisplayValue('Work laptop');
    await user.clear(renameInput);
    await user.type(renameInput, 'Phone');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.saveRename' }));

    expect(await screen.findByText('passkeyCancelled')).toBeInTheDocument();
    expect(apiMocks.renamePasskey).not.toHaveBeenCalled();
  });

  it('does not send a rename PATCH when fresh-auth is unsupported by the browser', async () => {
    const user = setupUser();
    const unsupportedError = new DOMException('Unsupported', 'NotSupportedError');
    apiMocks.requestPasskeyFreshAuthGrant.mockRejectedValueOnce(unsupportedError);
    apiMocks.mapPasskeyErrorMessageKey.mockReturnValueOnce('passkeyUnsupported');
    renderDashboard('security');

    await screen.findByText('Work laptop');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.renameAction' }));
    const renameInput = screen.getByDisplayValue('Work laptop');
    await user.clear(renameInput);
    await user.type(renameInput, 'Phone');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.saveRename' }));

    expect(await screen.findByText('passkeyUnsupported')).toBeInTheDocument();
    expect(apiMocks.mapPasskeyErrorMessageKey).toHaveBeenCalledWith(unsupportedError);
    expect(apiMocks.renamePasskey).not.toHaveBeenCalled();
    expect(apiMocks.deletePasskey).not.toHaveBeenCalled();
    expect(screen.getByDisplayValue('Phone')).toBeInTheDocument();
    expect(screen.queryByText('feedback.passkeyRenamed')).not.toBeInTheDocument();
  });

  it('does not mark rename as successful when the backend requires fresh-auth', async () => {
    const user = setupUser();
    apiMocks.requestPasskeyFreshAuthGrant.mockResolvedValueOnce('fresh-rename-grant');
    apiMocks.renamePasskey.mockRejectedValueOnce(
      new Error('Fresh passkey reauthentication required'),
    );
    renderDashboard('security');

    await screen.findByText('Work laptop');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.renameAction' }));
    const renameInput = screen.getByDisplayValue('Work laptop');
    await user.clear(renameInput);
    await user.type(renameInput, 'Phone');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.saveRename' }));

    expect(await screen.findByText('feedback.passkeyFailed')).toBeInTheDocument();
    expect(screen.queryByText('feedback.passkeyRenamed')).not.toBeInTheDocument();
  });

  it('reauthenticates before deleting a passkey and sends the fresh-auth grant', async () => {
    const user = setupUser();
    apiMocks.requestPasskeyFreshAuthGrant.mockResolvedValueOnce('fresh-delete-grant');
    renderDashboard('security');

    await screen.findByText('Work laptop');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.deleteAction' }));

    await waitFor(() => {
      expect(apiMocks.requestPasskeyFreshAuthGrant).toHaveBeenCalledWith(
        `passkey.credential.revoke:${passkeys.credentials[0].id}`,
      );
      expect(apiMocks.deletePasskey).toHaveBeenCalledWith(passkeys.credentials[0].id, {
        freshAuthGrantId: 'fresh-delete-grant',
      });
    });
    expect(apiMocks.requestPasskeyFreshAuthGrant.mock.invocationCallOrder[0]).toBeLessThan(
      apiMocks.deletePasskey.mock.invocationCallOrder[0],
    );
    expect(await screen.findByText('feedback.passkeyDeleted')).toBeInTheDocument();
  });

  it('does not delete a passkey when fresh-auth ceremony is cancelled', async () => {
    const user = setupUser();
    apiMocks.requestPasskeyFreshAuthGrant.mockRejectedValueOnce(
      new DOMException('Cancelled', 'AbortError'),
    );
    apiMocks.mapPasskeyErrorMessageKey.mockReturnValueOnce('passkeyCancelled');
    renderDashboard('security');

    await screen.findByText('Work laptop');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.deleteAction' }));

    expect(await screen.findByText('passkeyCancelled')).toBeInTheDocument();
    expect(apiMocks.deletePasskey).not.toHaveBeenCalled();
    expect(screen.getByText('Work laptop')).toBeInTheDocument();
  });

  it('does not send a delete request when fresh-auth is unsupported by the browser', async () => {
    const user = setupUser();
    const unsupportedError = new DOMException('Unsupported', 'NotSupportedError');
    apiMocks.requestPasskeyFreshAuthGrant.mockRejectedValueOnce(unsupportedError);
    apiMocks.mapPasskeyErrorMessageKey.mockReturnValueOnce('passkeyUnsupported');
    renderDashboard('security');

    await screen.findByText('Work laptop');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.deleteAction' }));

    expect(await screen.findByText('passkeyUnsupported')).toBeInTheDocument();
    expect(apiMocks.mapPasskeyErrorMessageKey).toHaveBeenCalledWith(unsupportedError);
    expect(apiMocks.renamePasskey).not.toHaveBeenCalled();
    expect(apiMocks.deletePasskey).not.toHaveBeenCalled();
    expect(screen.getByText('Work laptop')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'security.passkeys.deleteAction' })).toBeEnabled();
    expect(screen.queryByText('feedback.passkeyDeleted')).not.toBeInTheDocument();
  });

  it('keeps the credential visible when delete is rejected for missing fresh-auth', async () => {
    const user = setupUser();
    apiMocks.requestPasskeyFreshAuthGrant.mockResolvedValueOnce('fresh-delete-grant');
    apiMocks.deletePasskey.mockRejectedValueOnce(
      new Error('Fresh passkey reauthentication required'),
    );
    renderDashboard('security');

    await screen.findByText('Work laptop');
    await user.click(screen.getByRole('button', { name: 'security.passkeys.deleteAction' }));

    expect(await screen.findByText('feedback.passkeyFailed')).toBeInTheDocument();
    expect(screen.getByText('Work laptop')).toBeInTheDocument();
  });
});
