import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthGuard } from '../AuthGuard';

const { mockPush, mockMe, mockSetState } = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockMe: vi.fn(),
  mockSetState: vi.fn(),
}));

let currentAuthState: { isAuthenticated: boolean; user: Record<string, unknown> | null } = {
  isAuthenticated: false,
  user: null,
};

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => '/dashboard/servers',
}));

vi.mock('lucide-react', () => ({
  Loader2: (props: Record<string, unknown>) => <div data-testid="loader" {...props} />,
}));

vi.mock('@/lib/api/auth', () => ({
  authApi: {
    session: (...args: unknown[]) => mockMe(...args),
  },
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: Object.assign(() => ({}), {
    setState: (...args: unknown[]) => {
      mockSetState(...args);
      const patch = args[0] as Record<string, unknown>;
      currentAuthState = {
        ...currentAuthState,
        isAuthenticated: (patch.isAuthenticated as boolean | undefined) ?? currentAuthState.isAuthenticated,
        user: (patch.user as Record<string, unknown> | null | undefined) ?? currentAuthState.user,
      };
    },
    getState: () => currentAuthState,
  }),
}));

describe('AuthGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockReset();
    mockMe.mockReset();
    mockSetState.mockReset();
    currentAuthState = { isAuthenticated: false, user: null };
  });

  it('calls authApi.session on mount', async () => {
    mockMe.mockResolvedValueOnce({
      data: {
        id: 'user-1',
        email: 'user@example.com',
        role: 'viewer',
        is_active: true,
        is_email_verified: true,
        created_at: new Date().toISOString(),
      },
    });

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(mockMe).toHaveBeenCalledTimes(1);
    });
  });

  it('renders children when session check succeeds', async () => {
    mockMe.mockResolvedValueOnce({
      data: {
        id: 'user-1',
        email: 'user@example.com',
        role: 'viewer',
        is_active: true,
        is_email_verified: true,
        created_at: new Date().toISOString(),
      },
    });

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(mockSetState).toHaveBeenCalledWith(
      expect.objectContaining({
        isAuthenticated: true,
      }),
    );
  });

  it('redirects to login when session check fails', async () => {
    mockMe.mockRejectedValueOnce(new Error('401'));

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login?redirect=%2Fdashboard%2Fservers');
    });

    expect(mockSetState).toHaveBeenCalledWith(
      expect.objectContaining({
        isAuthenticated: false,
      }),
    );
  });

  it('shows loading state while auth check is in-flight', () => {
    mockMe.mockImplementationOnce(
      () =>
        new Promise(() => {
          // Intentionally unresolved promise to keep loading state.
        }),
    );

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    expect(screen.getByText('AUTHENTICATING...')).toBeInTheDocument();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
  });
});
