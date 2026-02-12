import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MagicLinkPage from '../page';

// -- Mocks --

const mockRequestMagicLink = vi.fn();
const mockClearError = vi.fn();

let mockStoreState = {
  requestMagicLink: mockRequestMagicLink,
  isLoading: false,
  error: null as string | null,
  clearError: mockClearError,
};

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => mockStoreState,
}));

// Mock auth feature components
vi.mock('@/features/auth/components', async () => {
  const React = await import('react');
  return {
    AuthFormCard: ({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) => {
      return React.createElement('div', { 'data-testid': 'auth-form-card' },
        React.createElement('h1', null, title),
        React.createElement('p', null, subtitle),
        children
      );
    },
    CyberInput: ({
      label,
      type,
      placeholder,
      value,
      onChange,
      required,
      disabled,
    }: Record<string, unknown>) => {
      return React.createElement('div', null,
        React.createElement('label', { htmlFor: 'cyber-input' }, label as string),
        React.createElement('input', {
          id: 'cyber-input',
          type,
          placeholder,
          value,
          onChange,
          required,
          disabled,
          'aria-label': label as string,
        })
      );
    },
    RateLimitCountdown: () => null,
    useIsRateLimited: () => false,
  };
});

// Mock @/components/ui/button
vi.mock('@/components/ui/button', async () => {
  const React = await import('react');
  return {
    Button: ({
      children,
      onClick,
      type,
      disabled,
      className,
      ...props
    }: Record<string, unknown>) => {
      return React.createElement('button', {
        onClick,
        type: type || 'button',
        disabled,
        className,
        ...props,
      }, children as React.ReactNode);
    },
  };
});

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => {
    const t = (key: string) => key;
    return t;
  },
}));

// Mock lucide-react
vi.mock('lucide-react', async () => {
  const React = await import('react');
  return {
    Mail: (props: Record<string, unknown>) => {
      return React.createElement('span', { ...props, 'data-testid': 'mail-icon' });
    },
    Loader2: (props: Record<string, unknown>) => {
      return React.createElement('span', { ...props, 'data-testid': 'loader-icon' });
    },
    CheckCircle: (props: Record<string, unknown>) => {
      return React.createElement('span', { ...props, 'data-testid': 'check-icon' });
    },
    AlertCircle: (props: Record<string, unknown>) => {
      return React.createElement('span', { ...props, 'data-testid': 'alert-icon' });
    },
  };
});

// Mock next/link
vi.mock('next/link', async () => {
  const React = await import('react');
  return {
    default: ({ children, href, ...props }: Record<string, unknown>) => {
      return React.createElement('a', { href, ...props }, children as React.ReactNode);
    },
  };
});

describe('MagicLinkPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStoreState = {
      requestMagicLink: mockRequestMagicLink,
      isLoading: false,
      error: null,
      clearError: mockClearError,
    };
  });

  it('renders the email input form', () => {
    render(<MagicLinkPage />);

    // Title should be present (translation key)
    expect(screen.getByText('title')).toBeInTheDocument();
    expect(screen.getByText('subtitle')).toBeInTheDocument();

    // Email input should be present
    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('type', 'email');

    // Submit button should be present
    const submitButton = screen.getByRole('button', { name: /submitButton/i });
    expect(submitButton).toBeInTheDocument();
  });

  it('submits email and calls requestMagicLink', async () => {
    const user = userEvent.setup();
    mockRequestMagicLink.mockResolvedValue(undefined);

    render(<MagicLinkPage />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'user@example.com');

    const submitButton = screen.getByRole('button', { name: /submitButton/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockRequestMagicLink).toHaveBeenCalledWith('user@example.com');
    });
  });

  it('shows success message after send', async () => {
    const user = userEvent.setup();
    mockRequestMagicLink.mockResolvedValue(undefined);

    render(<MagicLinkPage />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'success@example.com');

    const submitButton = screen.getByRole('button', { name: /submitButton/i });
    await user.click(submitButton);

    await waitFor(() => {
      // After successful send, should show "checkInbox" message
      expect(screen.getByText('checkInbox')).toBeInTheDocument();
    });

    // The email address should be displayed in the success message
    expect(screen.getByText('success@example.com')).toBeInTheDocument();
  });

  it('shows error message on failure', () => {
    mockStoreState = {
      ...mockStoreState,
      error: 'Failed to send magic link',
    };

    render(<MagicLinkPage />);

    // Error should be shown via role="alert"
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(screen.getByText('Failed to send magic link')).toBeInTheDocument();
  });

  it('clears error on mount', () => {
    render(<MagicLinkPage />);

    expect(mockClearError).toHaveBeenCalled();
  });

  it('disables submit when loading', () => {
    mockStoreState = {
      ...mockStoreState,
      isLoading: true,
    };

    render(<MagicLinkPage />);

    // The submit button should be disabled during loading
    const submitButton = screen.getByRole('button', { name: /submitting/i });
    expect(submitButton).toBeDisabled();
  });

  it('has a back to login link', () => {
    render(<MagicLinkPage />);

    const backLink = screen.getByText('backToLogin');
    expect(backLink).toBeInTheDocument();
    expect(backLink.closest('a')).toHaveAttribute('href', '/login');
  });
});
