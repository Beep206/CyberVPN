import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthGuard } from '../AuthGuard';

const mockPush = vi.fn();
vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => '/dashboard/servers',
}));

vi.mock('lucide-react', () => ({
  Loader2: (props: Record<string, unknown>) => <div data-testid="loader" {...props} />,
}));

const mockFetchUser = vi.fn();

let storeState = {
  isAuthenticated: false,
  isLoading: false,
  fetchUser: mockFetchUser,
};

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => storeState,
}));

describe('AuthGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockReset();
    mockFetchUser.mockReset();
    storeState = {
      isAuthenticated: false,
      isLoading: false,
      fetchUser: mockFetchUser,
    };
  });

  it('calls fetchUser when isAuthenticated is false', async () => {
    mockFetchUser.mockRejectedValueOnce(new Error('401'));

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(mockFetchUser).toHaveBeenCalledTimes(1);
    });
  });

  it('renders children when fetchUser succeeds', async () => {
    mockFetchUser.mockImplementationOnce(async () => {
      storeState = { ...storeState, isAuthenticated: true };
    });

    // Start unauthenticated, fetchUser will set isAuthenticated=true
    const { rerender } = render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    // Simulate the store update after fetchUser
    storeState = { ...storeState, isAuthenticated: true };
    rerender(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });

  it('redirects to login when fetchUser fails', async () => {
    mockFetchUser.mockRejectedValueOnce(new Error('401'));

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(
        '/login?redirect=%2Fdashboard%2Fservers',
      );
    });
  });

  it('does not call fetchUser if already authenticated', async () => {
    storeState = { ...storeState, isAuthenticated: true };

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(mockFetchUser).not.toHaveBeenCalled();
  });

  it('shows loading state while checking auth', () => {
    storeState = { ...storeState, isLoading: true };

    render(
      <AuthGuard>
        <div>Dashboard</div>
      </AuthGuard>,
    );

    expect(screen.getByText('AUTHENTICATING...')).toBeInTheDocument();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
  });
});
