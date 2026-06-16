import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UserMenu } from '../user-menu';

const apiMocks = vi.hoisted(() => ({
  getProfile: vi.fn(),
  logout: vi.fn(),
  push: vi.fn(),
  refresh: vi.fn(),
}));

const authState = vi.hoisted(() => ({
  isAuthenticated: true,
  user: {
    created_at: '2026-06-10T08:00:00Z',
    email: 'operator@example.com',
    id: 'user-123456',
    public_uid: 14677650 as number | null,
    is_active: true,
    is_email_verified: true,
    login: 'fallback_login',
    role: 'user' as const,
  },
}));

const messages = {
  Header: {
    userMenu: {
      triggerLabel: 'Open account menu for {name}',
      fallbackName: 'User',
      fallbackInitials: 'U',
      accountBadge: 'ACCOUNT',
      accountId: 'ID: {id}',
      signOut: 'Sign out',
      items: {
        dashboard: {
          label: 'Dashboard',
          description: 'Overview and stats',
        },
        profile: {
          label: 'Profile',
          description: 'Account details',
        },
        security: {
          label: 'Security',
          description: '2FA and password',
        },
        billing: {
          label: 'Billing',
          description: 'Manage plan',
        },
        settings: {
          label: 'Settings',
          description: 'App preferences',
        },
      },
    },
  },
};

function readMessage(path: string) {
  return path.split('.').reduce<unknown>((current, segment) => {
    if (current && typeof current === 'object' && segment in current) {
      return (current as Record<string, unknown>)[segment];
    }

    return undefined;
  }, messages);
}

vi.mock('next-intl', () => ({
  useTranslations: (namespace: string) => (key: string, params?: Record<string, string>) => {
    const value = readMessage(`${namespace}.${key}`);
    const template = typeof value === 'string' ? value : key;

    return Object.entries(params ?? {}).reduce(
      (result, [paramKey, paramValue]) => result.replace(`{${paramKey}}`, paramValue),
      template,
    );
  },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    refresh: apiMocks.refresh,
    replace: apiMocks.push,
  }),
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...props
  }: {
    children: ReactNode;
    href: string;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('@/shared/ui/magnetic-button', () => ({
  MagneticButton: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock('@/shared/ui/atoms/cypher-text', () => ({
  CypherText: ({ text }: { text: string }) => <span>{text}</span>,
}));

vi.mock('@/lib/api', () => ({
  profileApi: {
    getProfile: apiMocks.getProfile,
  },
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: (selector: (state: typeof authState & { logout: () => Promise<void> }) => unknown) =>
    selector({
      ...authState,
      logout: apiMocks.logout,
    }),
}));

function renderMenu() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <UserMenu />
    </QueryClientProvider>,
  );
}

describe('UserMenu', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.user = {
      ...authState.user,
      id: '7d871bc5-af6c-49b2-a3e6-e77eec938021',
      public_uid: 14677650,
    };
    apiMocks.getProfile.mockResolvedValue({
      data: {
        display_name: 'Cipher Prime',
      },
    });
    apiMocks.logout.mockResolvedValue(undefined);
  });

  it('uses profile display name and localized account menu labels', async () => {
    const user = userEvent.setup();
    renderMenu();

    const trigger = await screen.findByRole('button', {
      name: 'Open account menu for Cipher Prime',
    });
    await user.click(trigger);

    expect(apiMocks.getProfile).toHaveBeenCalledTimes(1);
    expect(screen.getAllByText('Cipher Prime').length).toBeGreaterThan(0);
    expect(screen.getByText('Overview and stats')).toBeInTheDocument();
    expect(screen.getByText('2FA and password')).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /Security/ })).toHaveAttribute(
      'href',
      '/settings/security',
    );
    expect(screen.getByText('ID: 14677650')).toBeInTheDocument();
    expect(screen.queryByText(/7d87/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
  });

  it('does not expose the internal UUID when public UID is absent', async () => {
    authState.user = {
      ...authState.user,
      id: '7d871bc5-af6c-49b2-a3e6-e77eec938021',
      public_uid: null,
    };
    const user = userEvent.setup();
    renderMenu();

    await user.click(await screen.findByRole('button', {
      name: 'Open account menu for Cipher Prime',
    }));

    expect(screen.queryByText(/ID:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/7d871bc5/)).not.toBeInTheDocument();
  });

  it('redirects away from authenticated UI before logout attempt finishes', async () => {
    const user = userEvent.setup();
    let resolveLogout: () => void;
    apiMocks.logout.mockReturnValueOnce(
      new Promise<void>((resolve) => {
        resolveLogout = resolve;
      }),
    );

    renderMenu();

    await user.click(await screen.findByRole('button', {
      name: 'Open account menu for Cipher Prime',
    }));
    await user.click(screen.getByRole('button', { name: 'Sign out' }));

    expect(apiMocks.logout).toHaveBeenCalledTimes(1);
    expect(apiMocks.push).toHaveBeenCalledWith('/');
    expect(apiMocks.refresh).toHaveBeenCalledTimes(1);

    resolveLogout!();

    await waitFor(() => {
      expect(apiMocks.push).toHaveBeenCalledWith('/');
    });
    expect(apiMocks.refresh).toHaveBeenCalledTimes(1);
  });
});
