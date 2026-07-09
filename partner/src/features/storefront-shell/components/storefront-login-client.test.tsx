import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StorefrontLoginClient } from './storefront-login-client';

const { mockLogin, mockPush, mockSearchParams, mockSession } = vi.hoisted(() => ({
  mockLogin: vi.fn(),
  mockPush: vi.fn(),
  mockSearchParams: vi.fn(() => new URLSearchParams()),
  mockSession: vi.fn(),
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

vi.mock('@/lib/api/auth', () => ({
  authApi: {
    login: mockLogin,
    session: mockSession,
  },
}));

describe('StorefrontLoginClient redirects', () => {
  beforeEach(() => {
    mockLogin.mockReset();
    mockPush.mockClear();
    mockSearchParams.mockReturnValue(new URLSearchParams());
    mockSession.mockReset();
  });

  it('pushes already localized post-login redirects without adding a second locale prefix', async () => {
    mockLogin.mockResolvedValue({ data: { requires_2fa: false, tfa_token: null } });
    mockSession.mockResolvedValue({ data: { id: 'customer' } });
    mockSearchParams.mockReturnValue(new URLSearchParams('redirect=/en-EN/dashboard'));

    render(<StorefrontLoginClient title="Storefront sign in" subtitle="Secure checkout access" />);

    fireEvent.input(screen.getByLabelText('Email'), {
      target: { value: 'customer@example.com' },
    });
    fireEvent.input(screen.getByLabelText('Password'), {
      target: { value: 'Password123!' },
    });
    fireEvent.click(screen.getByRole('button', { name: /continue to checkout/i }));

    await waitFor(() =>
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'customer@example.com',
        password: 'Password123!',
      }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/ru-RU/dashboard'));
    expect(mockPush).not.toHaveBeenCalledWith('/ru-RU/ru-RU/dashboard');
  });
});
