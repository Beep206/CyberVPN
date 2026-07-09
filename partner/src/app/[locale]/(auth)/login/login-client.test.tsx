import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LoginClient } from './login-client';

const { authState, mockPush, mockSearchParams } = vi.hoisted(() => ({
  authState: {
    user: null,
    isLoading: false,
    isAuthenticated: false,
    isNewTelegramUser: false,
    isMiniApp: false,
    error: null,
    rateLimitUntil: null as number | null,
    login: vi.fn(),
    loginWithPasskey: vi.fn(),
    register: vi.fn(),
    verifyOtpAndLogin: vi.fn(),
    logout: vi.fn(),
    fetchUser: vi.fn(),
    clearError: vi.fn(),
    clearRateLimit: vi.fn(),
  },
  mockPush: vi.fn(),
  mockSearchParams: vi.fn(() => new URLSearchParams()),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => mockSearchParams(),
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: (selector?: (state: typeof authState) => unknown) =>
    selector ? selector(authState) : authState,
  useRateLimitUntil: () => authState.rateLimitUntil,
}));

describe('Partner LoginClient passkey UX', () => {
  beforeEach(() => {
    authState.isAuthenticated = false;
    authState.rateLimitUntil = null;
    mockPush.mockClear();
    mockSearchParams.mockReturnValue(new URLSearchParams());
  });

  it('renders explicit passkey action and WebAuthn autocomplete anchor', () => {
    render(<LoginClient />);

    expect(screen.getByRole('button', { name: 'passkeyButton' })).toBeInTheDocument();
    expect(screen.getByLabelText('emailLabel')).toHaveAttribute(
      'autocomplete',
      'username webauthn',
    );
  });

  it('pushes already localized post-login redirects without adding a second locale prefix', async () => {
    authState.isAuthenticated = true;
    mockSearchParams.mockReturnValue(new URLSearchParams('redirect=/en-EN/dashboard'));

    render(<LoginClient />);

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/ru-RU/dashboard'));
    expect(mockPush).not.toHaveBeenCalledWith('/ru-RU/ru-RU/dashboard');
  });
});
