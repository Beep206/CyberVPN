import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthGuard } from '../AuthGuard';
import { ACCESS_DENIED_ERROR_CODE } from '@/features/auth/lib/partner-access';

const { mockPush, mockMe, mockLogout, mockSetState } = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockMe: vi.fn(),
  mockLogout: vi.fn(),
  mockSetState: vi.fn(),
}));

let currentAuthState: { isAuthenticated: boolean; user: Record<string, unknown> | null } = {
  isAuthenticated: false,
  user: null,
};
let currentLocale = 'ru-RU';
let currentPathname = '/dashboard/servers';

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => currentPathname,
}));

vi.mock('next-intl', () => ({
  useLocale: () => currentLocale,
}));

vi.mock('lucide-react', () => ({
  Loader2: (props: Record<string, unknown>) => <div data-testid="loader" {...props} />,
}));

vi.mock('@/lib/api/auth', () => ({
  authApi: {
    session: (...args: unknown[]) => mockMe(...args),
    logout: (...args: unknown[]) => mockLogout(...args),
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
    mockLogout.mockReset();
    mockSetState.mockReset();
    currentAuthState = { isAuthenticated: false, user: null };
    currentLocale = 'ru-RU';
    currentPathname = '/dashboard/servers';
    window.history.replaceState({}, '', '/ru-RU/dashboard/servers');
  });

  it('calls authApi.session on mount', async () => {
    mockMe.mockResolvedValueOnce({
      data: {
        id: 'user-1',
        email: 'user@example.com',
        role: 'viewer',
        auth_realm_key: 'partner',
        audience: 'cybervpn:partner',
        principal_type: 'partner_operator',
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

  it('renders children when partner session check succeeds', async () => {
    mockMe.mockResolvedValueOnce({
      data: {
        id: 'user-1',
        email: 'partner@example.com',
        role: 'operator',
        auth_realm_key: 'partner',
        audience: 'cybervpn:partner',
        principal_type: 'partner_operator',
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

  it('logs out and redirects to access denied when session belongs to the wrong realm', async () => {
    mockMe.mockResolvedValueOnce({
      data: {
        id: 'user-1',
        email: 'user@example.com',
        role: 'admin',
        auth_realm_key: 'admin',
        audience: 'cybervpn:admin',
        principal_type: 'admin',
        is_active: true,
        is_email_verified: true,
        created_at: new Date().toISOString(),
      },
    });
    mockLogout.mockResolvedValueOnce({});

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledTimes(1);
      expect(mockPush).toHaveBeenCalledWith(`/login?error=${ACCESS_DENIED_ERROR_CODE}`);
    });

    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
  });

  it('redirects to login when session check fails', async () => {
    mockMe.mockRejectedValueOnce(new Error('401'));

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login?redirect=%2Fru-RU%2Fdashboard%2Fservers');
    });

    expect(mockSetState).toHaveBeenCalledWith(
      expect.objectContaining({
        isAuthenticated: false,
      }),
    );
  });

  it('restores an existing authenticated partner session when a later network error occurs', async () => {
    currentAuthState = {
      isAuthenticated: true,
      user: {
        id: 'user-1',
        email: 'partner@example.com',
        role: 'operator',
        auth_realm_key: 'partner',
        audience: 'cybervpn:partner',
        principal_type: 'partner_operator',
      },
    };
    mockMe.mockRejectedValueOnce({ response: { status: 503 } });

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(mockPush).not.toHaveBeenCalled();
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

  it('redirects public auth paths to the localized dashboard target', async () => {
    currentPathname = '/login';
    mockMe.mockRejectedValueOnce(new Error('401'));

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login?redirect=%2Fru-RU%2Fdashboard');
    });
  });

  it('preserves the active locale when next-intl usePathname returns an internal route', async () => {
    currentLocale = 'ru-RU';
    currentPathname = '/dashboard';
    mockMe.mockRejectedValueOnce(new Error('401'));

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login?redirect=%2Fru-RU%2Fdashboard');
    });

    expect(mockPush).not.toHaveBeenCalledWith('/en-EN/login?redirect=%2Fdashboard');
  });
});
