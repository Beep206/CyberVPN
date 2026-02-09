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
vi.mock('@/features/auth/components', () => ({
  AuthFormCard: ({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) => {
    const { createElement } = require('react');
    return createElement('div', { 'data-testid': 'auth-form-card' },
      createElement('h1', null, title),
      createElement('p', null, subtitle),
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
    ..._rest
  }: Record<string, unknown>) => {
    const { createElement } = require('react');
    return createElement('div', null,
      createElement('label', { htmlFor: 'cyber-input' }, label as string),
      createElement('input', {
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
}));

// Mock @/components/ui/button
vi.mock('@/components/ui/button', () => ({
  Button: ({
    children,
    onClick,
    type,
    disabled,
    className,
    ...props
  }: Record<string, unknown>) => {
    const { createElement } = require('react');
    return createElement('button', {
      onClick,
      type: type || 'button',
      disabled,
      className,
      ...props,
    }, children);
  },
}));

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => {
    const t = (key: string) => key;
    return t;
  },
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Mail: (props: Record<string, unknown>) => {
    const { createElement } = require('react');
    return createElement('span', { ...props, 'data-testid': 'mail-icon' });
  },
  Loader2: (props: Record<string, unknown>) => {
    const { createElement } = require('react');
    return createElement('span', { ...props, 'data-testid': 'loader-icon' });
  },
  CheckCircle: (props: Record<string, unknown>) => {
    const { createElement } = require('react');
    return createElement('span', { ...props, 'data-testid': 'check-icon' });
  },
  AlertCircle: (props: Record<string, unknown>) => {
    const { createElement } = require('react');
    return createElement('span', { ...props, 'data-testid': 'alert-icon' });
  },
}));

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: Record<string, unknown>) => {
    const { createElement } = require('react');
    return createElement('a', { href, ...props }, children);
  },
}));

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
