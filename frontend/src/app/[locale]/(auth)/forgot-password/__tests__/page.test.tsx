import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ForgotPasswordPage from '../page';

const forgotPasswordMock = vi.hoisted(() => vi.fn());
const clearErrorMock = vi.hoisted(() => vi.fn());

vi.mock('@/lib/api/auth', () => ({
  authApi: {
    forgotPassword: forgotPasswordMock,
  },
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => ({
    clearError: clearErrorMock,
    isLoading: false,
  }),
}));

vi.mock('@/features/auth/components', async () => {
  const React = await import('react');

  return {
    AuthFormCard: ({
      children,
      subtitle,
      title,
    }: {
      children: React.ReactNode;
      subtitle: string;
      title: string;
    }) => React.createElement(
      'section',
      null,
      React.createElement('h1', null, title),
      React.createElement('p', null, subtitle),
      children,
    ),
    CyberInput: ({
      disabled,
      label,
      onChange,
      placeholder,
      required,
      type,
      value,
    }: {
      disabled?: boolean;
      label: string;
      onChange: React.ChangeEventHandler<HTMLInputElement>;
      placeholder?: string;
      required?: boolean;
      type?: string;
      value: string;
    }) => React.createElement(
      'label',
      null,
      label,
      React.createElement('input', {
        'aria-label': label,
        disabled,
        onChange,
        placeholder,
        required,
        type,
        value,
      }),
    ),
    RateLimitCountdown: () => null,
    useIsRateLimited: () => false,
  };
});

vi.mock('@/components/ui/button', async () => {
  const React = await import('react');

  return {
    Button: ({
      children,
      disabled,
      onClick,
      type,
      ...props
    }: {
      children: React.ReactNode;
      disabled?: boolean;
      onClick?: React.MouseEventHandler<HTMLButtonElement>;
      type?: 'button' | 'submit' | 'reset';
    }) => React.createElement('button', {
      disabled,
      onClick,
      type: type ?? 'button',
      ...props,
    }, children),
  };
});

vi.mock('next/link', async () => {
  const React = await import('react');

  return {
    default: ({
      children,
      href,
      ...props
    }: {
      children: React.ReactNode;
      href: string;
    }) => React.createElement('a', { href, ...props }, children),
  };
});

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    forgotPasswordMock.mockResolvedValue({
      data: {
        message: 'If the email is registered, a reset code has been sent.',
      },
      status: 200,
    });
  });

  it('shows success only after the forgot-password request succeeds', async () => {
    const user = userEvent.setup();

    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText('emailLabel'), 'qa-reset@example.test');
    await user.click(screen.getByRole('button', { name: 'submitButton' }));

    await waitFor(() => {
      expect(forgotPasswordMock).toHaveBeenCalledWith({
        email: 'qa-reset@example.test',
      });
    });

    expect(await screen.findByText('successTitle')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows an error and keeps the email form when the request fails', async () => {
    const user = userEvent.setup();
    forgotPasswordMock.mockRejectedValueOnce(new Error('Request failed with status code 500'));

    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText('emailLabel'), 'qa-reset@example.test');
    await user.click(screen.getByRole('button', { name: 'submitButton' }));

    const alert = await screen.findByRole('alert');

    expect(alert).toHaveTextContent('serverError');
    expect(screen.queryByText('successTitle')).not.toBeInTheDocument();
    expect(screen.getByLabelText('emailLabel')).toHaveValue('qa-reset@example.test');
    expect(screen.getByRole('button', { name: 'submitButton' })).toBeEnabled();
  });
});
