import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LoginClient } from '../login-client';

const routerPush = vi.hoisted(() => vi.fn());

const authStore = vi.hoisted(() => ({
  clearError: vi.fn(),
  error: null as string | null,
  fetchUser: vi.fn(),
  isAuthenticated: false,
  isLoading: false,
  login: vi.fn(),
  oauthLogin: vi.fn(),
}));

const passkeyMocks = vi.hoisted(() => ({
  cancelPasskeyCeremony: vi.fn(),
  completePasskeyAuthentication: vi.fn(),
  getPasskeyBrowserSupport: vi.fn(),
  getPasskeyErrorMessageKey: vi.fn(() => 'passkeyGenericError'),
  getPolicy: vi.fn(),
}));

const twoFactorMocks = vi.hoisted(() => ({
  completePendingTwoFactorSession: vi.fn(),
  getPendingTwoFactorSession: vi.fn(),
  stagePendingTwoFactorSession: vi.fn(),
}));

const messages: Record<string, string> = {
  divider: 'OR',
  emailLabel: 'Email address',
  emailPlaceholder: 'Enter your email',
  forgotPassword: 'Forgot password?',
  magicLinkAlt: 'Sign in with magic link',
  noAccount: "Don't have an account?",
  passkeyButton: 'Sign in with passkey',
  passkeyChecking: 'Checking passkey...',
  passkeyFallbackHint: 'You can still use your password or another sign-in method.',
  passkeyGenericError: 'Could not verify this passkey.',
  passkeyUnsupported: 'This browser or device does not support passkeys.',
  passwordLabel: 'Password',
  rememberMe: 'Remember me',
  signUpLink: 'Sign up',
  submitButton: 'Sign In',
  submitting: 'Signing in...',
  subtitle: 'Access your secure connection',
  title: 'Sign In',
  twoFactorStartFailed: 'Two-factor verification could not start. Try signing in again.',
};

const defaultPasskeyPolicy = {
  enabled: true,
  authenticationEnabled: true,
  registrationEnabled: true,
  conditionalUiEnabled: true,
  reauthenticationEnabled: true,
  adminCountsAsMfa: false,
  allowedOrigins: ['http://localhost:3000'],
  browserTimeoutMs: 60000,
  challengeTtlSeconds: 120,
  realm_key: 'customer',
  rp_id: 'localhost',
  rp_name: 'CyberVPN',
  surface: 'frontend',
};

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => {
    const t = (key: string) => messages[key] ?? key;
    t.has = (key: string) => key in messages;
    return t;
  },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: routerPush,
  }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/lib/api', () => ({
  passkeysApi: {
    getPolicy: passkeyMocks.getPolicy,
  },
}));

vi.mock('@/features/auth/lib/passkey-webauthn', () => ({
  cancelPasskeyCeremony: passkeyMocks.cancelPasskeyCeremony,
  completePasskeyAuthentication: passkeyMocks.completePasskeyAuthentication,
  getPasskeyBrowserSupport: passkeyMocks.getPasskeyBrowserSupport,
  getPasskeyErrorMessageKey: passkeyMocks.getPasskeyErrorMessageKey,
}));

vi.mock('@/features/auth/lib/pending-twofa-client', () => ({
  completePendingTwoFactorSession: twoFactorMocks.completePendingTwoFactorSession,
  getPendingTwoFactorSession: twoFactorMocks.getPendingTwoFactorSession,
  stagePendingTwoFactorSession: twoFactorMocks.stagePendingTwoFactorSession,
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => authStore,
  useRateLimitUntil: () => null,
}));

describe('LoginClient passkeys', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authStore.error = null;
    authStore.isAuthenticated = false;
    authStore.isLoading = false;
    authStore.fetchUser.mockResolvedValue(undefined);
    passkeyMocks.getPolicy.mockResolvedValue({
      data: defaultPasskeyPolicy,
    });
    passkeyMocks.getPasskeyBrowserSupport.mockResolvedValue({
      autofill: true,
      secureContext: true,
      webAuthn: true,
    });
    passkeyMocks.completePasskeyAuthentication.mockResolvedValue({
      data: {
        access_token: 'cookie-managed',
        refresh_token: 'cookie-managed',
        token_type: 'bearer',
        expires_in: 3600,
        requires_2fa: false,
        tfa_token: null,
      },
    });
  });

  it('shows explicit passkey login and enables Conditional UI autocomplete', async () => {
    render(<LoginClient />);

    expect(
      await screen.findByRole('button', { name: 'Sign in with passkey' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Email address')).toHaveAttribute(
      'autocomplete',
      'username webauthn',
    );
  });

  it('finishes explicit passkey login through the existing cookie session model', async () => {
    passkeyMocks.getPolicy.mockResolvedValueOnce({
      data: {
        ...defaultPasskeyPolicy,
        conditionalUiEnabled: false,
      },
    });

    const user = userEvent.setup();
    render(<LoginClient />);

    await user.click(await screen.findByRole('button', { name: 'Sign in with passkey' }));

    await waitFor(() => {
      expect(passkeyMocks.completePasskeyAuthentication).toHaveBeenCalledWith(
        expect.objectContaining({ conditional: false }),
      );
      expect(authStore.fetchUser).toHaveBeenCalled();
      expect(routerPush).toHaveBeenCalledWith('/en-EN/dashboard');
    });
  });

  it('shows a fallback note when backend allows passkeys but the browser does not', async () => {
    passkeyMocks.getPasskeyBrowserSupport.mockResolvedValueOnce({
      autofill: false,
      secureContext: true,
      webAuthn: false,
    });

    render(<LoginClient />);

    expect(
      await screen.findByText(/This browser or device does not support passkeys/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Sign in with passkey' }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument();
  });
});
