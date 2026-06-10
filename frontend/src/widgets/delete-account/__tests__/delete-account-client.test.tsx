import type React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DeleteAccountClient } from '../delete-account-client';

const { deleteAccountMock, routerPushMock } = vi.hoisted(() => ({
  deleteAccountMock: vi.fn(),
  routerPushMock: vi.fn(),
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
  useRouter: () => ({
    push: routerPushMock,
  }),
}));

vi.mock('next-intl', () => ({
  useTranslations:
    () =>
    (key: string) => {
      const messages: Record<string, string> = {
        'form.cancel': 'Cancel',
        'form.submit': 'Delete My Account',
        'form.submitting': 'Deleting...',
      };

      return messages[key] ?? key;
    },
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: (
    selector: (state: { deleteAccount: typeof deleteAccountMock }) => unknown,
  ) => selector({ deleteAccount: deleteAccountMock }),
  useIsAuthenticated: () => true,
}));

function renderDeleteAccountClient() {
  render(<DeleteAccountClient />);
}

describe('DeleteAccountClient', () => {
  it('stacks destructive actions on mobile and keeps both actions full width', () => {
    renderDeleteAccountClient();

    const submit = screen.getByRole('button', { name: 'Delete My Account' });
    const cancel = screen.getByRole('link', { name: 'Cancel' });
    const actions = submit.parentElement;

    expect(actions).toHaveClass('flex-col', 'sm:flex-row');
    expect(submit).toHaveClass('min-h-12', 'w-full', 'sm:flex-1');
    expect(cancel).toHaveClass('min-h-12', 'w-full', 'sm:flex-1');
  });
});
