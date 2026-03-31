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
    oauthStarted: vi.fn(),
    oauthCallbackSuccess: vi.fn(),
    oauthCallbackFailed: vi.fn(),
    oauthTwoFactorRequired: vi.fn(),
    oauthCollision: vi.fn(),
    oauthProviderDenied: vi.fn(),
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
// Store configuration tests
// ---------------------------------------------------------------------------

describe('Auth Store - configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStoreState();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('test_store_does_not_expose_persist_middleware_api', () => {
    expect((useAuthStore as unknown as { persist?: unknown }).persist).toBeUndefined();
  });

  it('test_store_runtime_state_is_ephemeral_by_default', () => {
    const state = useAuthStore.getState();

    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });
});

describe('Auth Store - oauthLogin analytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStoreState();
    window.location.origin = 'http://localhost:3000';
    window.location.pathname = '/ru-RU/login';
    window.location.search = '';
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('test_oauthLogin_tracks_started_event_before_navigation', async () => {
    const { authAnalytics } = await import('@/lib/analytics');

    await useAuthStore.getState().oauthLogin('github');

    expect(authAnalytics.oauthStarted).toHaveBeenCalledWith('github');
    expect(window.location.href).toBe(
      'http://localhost:3000/api/oauth/start/github?locale=ru-RU&return_to=%2Fru-RU%2Fdashboard',
    );
  });
});
