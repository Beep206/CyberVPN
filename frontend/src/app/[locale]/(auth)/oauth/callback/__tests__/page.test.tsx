import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import OAuthCallbackPage from '../page';

// -- Mocks --

const mockPush = vi.fn();

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    back: vi.fn(),
  }),
}));

// Mock useSearchParams with configurable return
let mockSearchParams = new URLSearchParams();

vi.mock('next/navigation', () => ({
  useSearchParams: () => mockSearchParams,
}));

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => {
    const t = (key: string) => key;
    return t;
  },
}));

// Mock useAuthStore
const mockOauthCallback = vi.fn();

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => ({
    oauthCallback: mockOauthCallback,
  }),
}));

// Mock @/components/ui/button
vi.mock('@/components/ui/button', async () => {
  const React = await import('react');
  return {
    Button: ({ children, onClick, ...props }: { children?: React.ReactNode; onClick?: React.MouseEventHandler } & Record<string, unknown>) => {
      return React.createElement('button', { onClick, ...props }, children as React.ReactNode);
    },
  };
});

// Mock lucide-react icons
vi.mock('lucide-react', async () => {
  const React = await import('react');
  return {
    Loader2: ({ className, ...props }: Record<string, unknown>) => {
      return React.createElement('span', { className, ...props, 'data-testid': 'loader-icon' });
    },
    AlertCircle: ({ className, ...props }: Record<string, unknown>) => {
      return React.createElement('span', { className, ...props, 'data-testid': 'alert-icon' });
    },
    RotateCcw: ({ className, ...props }: Record<string, unknown>) => {
      return React.createElement('span', { className, ...props, 'data-testid': 'retry-icon' });
    },
    Shield: ({ className, ...props }: Record<string, unknown>) => {
      return React.createElement('span', { className, ...props, 'data-testid': 'shield-icon' });
    },
  };
});

describe('OAuthCallbackPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
    sessionStorage.clear();
  });

  it('shows loading state initially when params are present', () => {
    mockSearchParams = new URLSearchParams('code=abc123&state=xyz789');
    sessionStorage.setItem('oauth_provider', 'google');

    // oauthCallback returns a pending promise to keep loading state
    mockOauthCallback.mockReturnValue(new Promise(() => {}));

    render(<OAuthCallbackPage />);

    // Should show the "authenticating" text (translation key)
    expect(screen.getByText('authenticating')).toBeInTheDocument();
    expect(screen.getByText('verifyingIdentity')).toBeInTheDocument();
  });

  it('calls oauthCallback with params from URL', async () => {
    mockSearchParams = new URLSearchParams('code=auth_code_123&state=csrf_state_456');
    sessionStorage.setItem('oauth_provider', 'github');

    mockOauthCallback.mockResolvedValue({
      requires_2fa: false,
      access_token: 'token',
      refresh_token: 'refresh',
      user: { id: '1', login: 'test', email: 'test@example.com', is_active: true, is_email_verified: true, created_at: '2024-01-01' },
    });

    render(<OAuthCallbackPage />);

    await waitFor(() => {
      expect(mockOauthCallback).toHaveBeenCalledWith('github', 'auth_code_123', 'csrf_state_456');
    });
  });

  it('redirects to dashboard on successful callback', async () => {
    mockSearchParams = new URLSearchParams('code=success_code&state=valid_state');
    sessionStorage.setItem('oauth_provider', 'google');

    mockOauthCallback.mockResolvedValue({
      requires_2fa: false,
      access_token: 'token',
      refresh_token: 'refresh',
      user: { id: '1', login: 'user', email: 'user@test.com', is_active: true, is_email_verified: true, created_at: '2024-01-01' },
    });

    render(<OAuthCallbackPage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('redirects to 2FA page when requires_2fa is true', async () => {
    mockSearchParams = new URLSearchParams('code=tfa_code&state=tfa_state');
    sessionStorage.setItem('oauth_provider', 'discord');

    mockOauthCallback.mockResolvedValue({
      requires_2fa: true,
      tfa_token: 'tfa_token_abc',
      access_token: '',
      refresh_token: '',
      user: { id: '1', login: 'user', email: 'u@t.com', is_active: true, is_email_verified: true, created_at: '2024-01-01' },
    });

    render(<OAuthCallbackPage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login?2fa=true');
    });
  });

  it('shows error state when oauthCallback fails', async () => {
    mockSearchParams = new URLSearchParams('code=bad_code&state=bad_state');
    sessionStorage.setItem('oauth_provider', 'apple');

    mockOauthCallback.mockRejectedValue({
      message: 'OAuth callback failed',
    });

    render(<OAuthCallbackPage />);

    await waitFor(() => {
      // The error message should be displayed
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    // Should show error title
    expect(screen.getByText('errorTitle')).toBeInTheDocument();
  });

  it('shows error when URL params are missing', () => {
    // No code or state in URL, no provider in sessionStorage
    mockSearchParams = new URLSearchParams();

    render(<OAuthCallbackPage />);

    // Should show error for missing params (translation key)
    expect(screen.getByText('missingParams')).toBeInTheDocument();
    expect(mockOauthCallback).not.toHaveBeenCalled();
  });

  it('shows error when code is missing from URL', () => {
    mockSearchParams = new URLSearchParams('state=some_state');
    sessionStorage.setItem('oauth_provider', 'google');

    render(<OAuthCallbackPage />);

    expect(screen.getByText('missingParams')).toBeInTheDocument();
    expect(mockOauthCallback).not.toHaveBeenCalled();
  });

  it('shows error when state is missing from URL', () => {
    mockSearchParams = new URLSearchParams('code=some_code');
    sessionStorage.setItem('oauth_provider', 'google');

    render(<OAuthCallbackPage />);

    expect(screen.getByText('missingParams')).toBeInTheDocument();
    expect(mockOauthCallback).not.toHaveBeenCalled();
  });

  it('shows error when provider is missing from sessionStorage', () => {
    mockSearchParams = new URLSearchParams('code=abc&state=xyz');
    // Not setting oauth_provider in sessionStorage

    render(<OAuthCallbackPage />);

    expect(screen.getByText('missingParams')).toBeInTheDocument();
    expect(mockOauthCallback).not.toHaveBeenCalled();
  });
});
