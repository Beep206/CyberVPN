import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import MagicLinkVerifyPage from '../page';

// -- Mocks --

const mockPush = vi.fn();

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    back: vi.fn(),
  }),
}));

let mockSearchParams = new URLSearchParams();

vi.mock('next/navigation', () => ({
  useSearchParams: () => mockSearchParams,
}));

vi.mock('next-intl', () => ({
  useTranslations: () => {
    const t = (key: string) => key;
    return t;
  },
}));

const mockVerifyMagicLink = vi.fn();
let mockIsAuthenticated = false;

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => ({
    verifyMagicLink: mockVerifyMagicLink,
    isAuthenticated: mockIsAuthenticated,
  }),
}));

// Mock @/components/ui/button
vi.mock('@/components/ui/button', async () => {
  const React = await import('react');
  return {
    Button: ({ children, onClick, ...props }: Record<string, unknown>) => {
      return React.createElement('button', { onClick, ...props }, children);
    },
  };
});

// Mock lucide-react
vi.mock('lucide-react', async () => {
  const React = await import('react');
  return {
    Loader2: (props: Record<string, unknown>) => {
      return React.createElement('span', { ...props, 'data-testid': 'loader-icon' });
    },
    AlertCircle: (props: Record<string, unknown>) => {
      return React.createElement('span', { ...props, 'data-testid': 'alert-icon' });
    },
    RotateCcw: (props: Record<string, unknown>) => {
      return React.createElement('span', { ...props, 'data-testid': 'retry-icon' });
    },
    Shield: (props: Record<string, unknown>) => {
      return React.createElement('span', { ...props, 'data-testid': 'shield-icon' });
    },
    CheckCircle: (props: Record<string, unknown>) => {
      return React.createElement('span', { ...props, 'data-testid': 'check-icon' });
    },
  };
});

describe('MagicLinkVerifyPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
    mockIsAuthenticated = false;
  });

  it('shows verifying state when token is present', () => {
    mockSearchParams = new URLSearchParams('token=valid_token_123');
    mockVerifyMagicLink.mockReturnValue(new Promise(() => {})); // Keep pending

    render(<MagicLinkVerifyPage />);

    expect(screen.getByText('verifying')).toBeInTheDocument();
    expect(screen.getByText('validating')).toBeInTheDocument();
  });

  it('calls verifyMagicLink with token from URL', async () => {
    mockSearchParams = new URLSearchParams('token=magic_abc_123');
    mockVerifyMagicLink.mockResolvedValue(undefined);

    render(<MagicLinkVerifyPage />);

    await waitFor(() => {
      expect(mockVerifyMagicLink).toHaveBeenCalledWith('magic_abc_123');
    });
  });

  it('shows error when token is missing from URL', () => {
    mockSearchParams = new URLSearchParams(); // No token

    render(<MagicLinkVerifyPage />);

    // Should show "missingToken" error text
    expect(screen.getByText('missingToken')).toBeInTheDocument();
    expect(mockVerifyMagicLink).not.toHaveBeenCalled();
  });

  it('shows error state when verification fails', async () => {
    mockSearchParams = new URLSearchParams('token=expired_token');
    mockVerifyMagicLink.mockRejectedValue({
      response: { data: { detail: 'Token expired' } },
    });

    render(<MagicLinkVerifyPage />);

    await waitFor(() => {
      // The error message should appear
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    // Shows the failed heading
    expect(screen.getByText('failed')).toBeInTheDocument();
  });

  it('shows fallback error message when detail is not available', async () => {
    mockSearchParams = new URLSearchParams('token=bad_token');
    mockVerifyMagicLink.mockRejectedValue(new Error('Network error'));

    render(<MagicLinkVerifyPage />);

    await waitFor(() => {
      // Should show the fallback "invalidOrExpired" translation key
      expect(screen.getByText('invalidOrExpired')).toBeInTheDocument();
    });
  });

  it('redirects to dashboard on successful verification when authenticated', async () => {
    mockSearchParams = new URLSearchParams('token=good_token');
    mockIsAuthenticated = true;
    mockVerifyMagicLink.mockResolvedValue(undefined);

    render(<MagicLinkVerifyPage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('shows success state after verification completes', async () => {
    mockSearchParams = new URLSearchParams('token=success_token');
    mockVerifyMagicLink.mockResolvedValue(undefined);

    render(<MagicLinkVerifyPage />);

    await waitFor(() => {
      expect(mockVerifyMagicLink).toHaveBeenCalledWith('success_token');
    });

    // After verification, should show "verified" text
    await waitFor(() => {
      expect(screen.getByText('verified')).toBeInTheDocument();
    });
  });
});
