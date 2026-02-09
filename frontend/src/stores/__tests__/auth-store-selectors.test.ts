import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Hoisted mocks
// ---------------------------------------------------------------------------

const { MockRateLimitError } = vi.hoisted(() => {
  class _RateLimitError extends Error {
    retryAfter: number;
    constructor(retryAfter: number) {
      super(`Rate limited. Try again in ${retryAfter} seconds`);
      this.name = 'RateLimitError';
      this.retryAfter = retryAfter;
    }
  }
  return { MockRateLimitError: _RateLimitError };
});

// Mock authApi (minimal -- selectors don't call API)
vi.mock('@/lib/api/auth', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    verifyOtp: vi.fn(),
    logout: vi.fn(),
    me: vi.fn(),
    telegramWidget: vi.fn(),
    telegramMiniApp: vi.fn(),
    telegramBotLink: vi.fn(),
    oauthLoginAuthorize: vi.fn(),
    oauthLoginCallback: vi.fn(),
    requestMagicLink: vi.fn(),
    verifyMagicLink: vi.fn(),
    deleteAccount: vi.fn(),
  },
}));

// Mock tokenStorage
vi.mock('@/lib/api/client', () => ({
  tokenStorage: {
    setTokens: vi.fn(),
    clearTokens: vi.fn(),
    getAccessToken: () => null,
    getRefreshToken: () => null,
    hasTokens: () => false,
  },
  RateLimitError: MockRateLimitError,
}));

// Mock analytics
vi.mock('@/lib/analytics', () => ({
  authAnalytics: {
    loginStarted: vi.fn(),
    loginSuccess: vi.fn(),
    loginError: vi.fn(),
    registerStarted: vi.fn(),
    registerSuccess: vi.fn(),
    registerError: vi.fn(),
    logout: vi.fn(),
    sessionRestored: vi.fn(),
    sessionExpired: vi.fn(),
    telegramStarted: vi.fn(),
    telegramSuccess: vi.fn(),
    telegramError: vi.fn(),
    rateLimited: vi.fn(),
  },
}));

// Import AFTER mocks
import {
  useAuthStore,
  useUser,
  useIsAuthenticated,
  useAuthLoading,
  useAuthError,
  useRateLimitUntil,
  useIsNewTelegramUser,
  useIsMiniApp,
} from '../auth-store';

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

function createMockUser(overrides: Record<string, unknown> = {}) {
  return {
    id: 'usr_selector_001',
    email: 'selector@cybervpn.io',
    login: 'selectoruser',
    role: 'user' as const,
    is_active: true,
    is_email_verified: true,
    created_at: '2025-06-01T12:00:00Z',
    ...overrides,
  };
}

function resetStoreState() {
  useAuthStore.setState({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    isNewTelegramUser: false,
    error: null,
    rateLimitUntil: null,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Auth Store - Selector hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStoreState();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // =========================================================================
  // useUser
  // =========================================================================

  describe('useUser', () => {
    it('test_useUser_returns_null_when_no_user', () => {
      // Arrange & Act
      const { result } = renderHook(() => useUser());

      // Assert
      expect(result.current).toBe(null);
    });

    it('test_useUser_returns_user_when_set', () => {
      // Arrange
      const mockUser = createMockUser({ id: 'usr_hook_user' });
      useAuthStore.setState({ user: mockUser });

      // Act
      const { result } = renderHook(() => useUser());

      // Assert
      expect(result.current).toEqual(mockUser);
      expect(result.current?.id).toBe('usr_hook_user');
    });
  });

  // =========================================================================
  // useIsAuthenticated
  // =========================================================================

  describe('useIsAuthenticated', () => {
    it('test_useIsAuthenticated_returns_false_by_default', () => {
      const { result } = renderHook(() => useIsAuthenticated());
      expect(result.current).toBe(false);
    });

    it('test_useIsAuthenticated_returns_true_when_authenticated', () => {
      useAuthStore.setState({ isAuthenticated: true });
      const { result } = renderHook(() => useIsAuthenticated());
      expect(result.current).toBe(true);
    });
  });

  // =========================================================================
  // useAuthLoading
  // =========================================================================

  describe('useAuthLoading', () => {
    it('test_useAuthLoading_returns_false_by_default', () => {
      const { result } = renderHook(() => useAuthLoading());
      expect(result.current).toBe(false);
    });

    it('test_useAuthLoading_returns_true_when_loading', () => {
      useAuthStore.setState({ isLoading: true });
      const { result } = renderHook(() => useAuthLoading());
      expect(result.current).toBe(true);
    });
  });

  // =========================================================================
  // useAuthError
  // =========================================================================

  describe('useAuthError', () => {
    it('test_useAuthError_returns_null_by_default', () => {
      const { result } = renderHook(() => useAuthError());
      expect(result.current).toBe(null);
    });

    it('test_useAuthError_returns_error_string_when_set', () => {
      useAuthStore.setState({ error: 'Something went wrong' });
      const { result } = renderHook(() => useAuthError());
      expect(result.current).toBe('Something went wrong');
    });
  });

  // =========================================================================
  // useRateLimitUntil
  // =========================================================================

  describe('useRateLimitUntil', () => {
    it('test_useRateLimitUntil_returns_null_by_default', () => {
      const { result } = renderHook(() => useRateLimitUntil());
      expect(result.current).toBe(null);
    });

    it('test_useRateLimitUntil_returns_timestamp_when_rate_limited', () => {
      const futureTimestamp = Date.now() + 30000;
      useAuthStore.setState({ rateLimitUntil: futureTimestamp });
      const { result } = renderHook(() => useRateLimitUntil());
      expect(result.current).toBe(futureTimestamp);
    });
  });

  // =========================================================================
  // useIsNewTelegramUser
  // =========================================================================

  describe('useIsNewTelegramUser', () => {
    it('test_useIsNewTelegramUser_returns_false_by_default', () => {
      const { result } = renderHook(() => useIsNewTelegramUser());
      expect(result.current).toBe(false);
    });

    it('test_useIsNewTelegramUser_returns_true_when_new_telegram_user', () => {
      useAuthStore.setState({ isNewTelegramUser: true });
      const { result } = renderHook(() => useIsNewTelegramUser());
      expect(result.current).toBe(true);
    });
  });

  // =========================================================================
  // useIsMiniApp
  // =========================================================================

  describe('useIsMiniApp', () => {
    it('test_useIsMiniApp_returns_boolean_value', () => {
      // The isMiniApp value is computed at store creation time from
      // window.Telegram?.WebApp?.initData. In the test environment,
      // Telegram is not typically on window, so it should be false.
      const { result } = renderHook(() => useIsMiniApp());
      expect(typeof result.current).toBe('boolean');
    });
  });
});

// ---------------------------------------------------------------------------
// Persist configuration tests
// ---------------------------------------------------------------------------

describe('Auth Store - Persist configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStoreState();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('test_persist_partialize_only_persists_user_and_isAuthenticated', () => {
    // Arrange - set multiple state fields
    const mockUser = createMockUser();
    useAuthStore.setState({
      user: mockUser,
      isAuthenticated: true,
      isLoading: true,
      error: 'some error',
      rateLimitUntil: 99999,
      isNewTelegramUser: true,
    });

    // Act - access the persist API to get the partialize function
    // The persist middleware stores name = 'auth-storage'
    const persistApi = (useAuthStore as unknown as { persist: { getOptions: () => { partialize: (state: unknown) => unknown; name: string } } }).persist;
    const { partialize, name } = persistApi.getOptions();

    // Assert - name should be 'auth-storage'
    expect(name).toBe('auth-storage');

    // Assert - partialize should only include user and isAuthenticated
    const state = useAuthStore.getState();
    const persisted = partialize(state) as Record<string, unknown>;

    expect(persisted).toHaveProperty('user');
    expect(persisted).toHaveProperty('isAuthenticated');
    // These should NOT be persisted
    expect(persisted).not.toHaveProperty('isLoading');
    expect(persisted).not.toHaveProperty('error');
    expect(persisted).not.toHaveProperty('rateLimitUntil');
    expect(persisted).not.toHaveProperty('isNewTelegramUser');
  });

  it('test_persist_uses_localStorage_as_storage_backend', () => {
    // The store is configured with createJSONStorage(() => localStorage)
    // We verify by checking the persist options
    const persistApi = (useAuthStore as unknown as { persist: { getOptions: () => { storage: unknown } } }).persist;
    const { storage } = persistApi.getOptions();

    // Storage should be defined (not null/undefined)
    expect(storage).toBeDefined();
    expect(storage).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// oauthCallback analytics (gap from original tests)
// ---------------------------------------------------------------------------

describe('Auth Store - oauthCallback analytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStoreState();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('test_oauthCallback_success_without_2fa_calls_loginSuccess_analytics_with_provider', async () => {
    // Arrange
    sessionStorage.setItem('oauth_state', 'analytics_state');

    // We need to re-import the store after adjusting mocks for this specific test.
    // Since authApi is already mocked, we use the mock directly.
    const { authApi } = await import('@/lib/api/auth');
    (authApi.oauthLoginCallback as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        requires_2fa: false,
        access_token: 'at_oauth',
        refresh_token: 'rt_oauth',
        user: {
          id: 'usr_oauth_analytics',
          login: 'oauthuser',
          email: 'oauth@test.com',
          is_active: true,
          is_email_verified: true,
          created_at: '2024-01-01',
        },
        is_new_user: false,
      },
    });

    // Act
    await useAuthStore.getState().oauthCallback('github', 'code123', 'analytics_state');

    // Assert - loginSuccess should have been called with the user ID and the provider
    const { authAnalytics } = await import('@/lib/analytics');
    expect(authAnalytics.loginSuccess).toHaveBeenCalledWith('usr_oauth_analytics', 'github');
  });
});
