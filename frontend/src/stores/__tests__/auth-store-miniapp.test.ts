import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// ---------------------------------------------------------------------------
// Hoisted mocks (vi.hoisted ensures these are available at mock-factory time)
// ---------------------------------------------------------------------------

const {
  mockTelegramMiniApp,
  mockMe,
  mockSetTokens,
  mockClearTokens,
  MockRateLimitError,
  mockLoginStarted,
  mockLoginSuccess,
  mockLoginError,
  mockAnalyticsLogout,
  mockSessionRestored,
  mockTelegramStarted,
  mockTelegramSuccess,
  mockTelegramError,
  mockRateLimited,
} = vi.hoisted(() => {
  class _RateLimitError extends Error {
    retryAfter: number;
    constructor(retryAfter: number) {
      super(`Rate limited. Try again in ${retryAfter} seconds`);
      this.name = 'RateLimitError';
      this.retryAfter = retryAfter;
    }
  }
  return {
    mockTelegramMiniApp: vi.fn(),
    mockMe: vi.fn(),
    mockSetTokens: vi.fn(),
    mockClearTokens: vi.fn(),
    MockRateLimitError: _RateLimitError,
    mockLoginStarted: vi.fn(),
    mockLoginSuccess: vi.fn(),
    mockLoginError: vi.fn(),
    mockAnalyticsLogout: vi.fn(),
    mockSessionRestored: vi.fn(),
    mockTelegramStarted: vi.fn(),
    mockTelegramSuccess: vi.fn(),
    mockTelegramError: vi.fn(),
    mockRateLimited: vi.fn(),
  };
});

// Mock authApi
vi.mock('@/lib/api/auth', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    verifyOtp: vi.fn(),
    logout: vi.fn(),
    me: (...args: unknown[]) => mockMe(...args),
    telegramWidget: vi.fn(),
    telegramMiniApp: (...args: unknown[]) => mockTelegramMiniApp(...args),
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
    setTokens: (...args: unknown[]) => mockSetTokens(...args),
    clearTokens: () => mockClearTokens(),
    getAccessToken: () => null,
    getRefreshToken: () => null,
    hasTokens: () => false,
  },
  RateLimitError: MockRateLimitError,
}));

// Mock analytics
vi.mock('@/lib/analytics', () => ({
  authAnalytics: {
    loginStarted: (...args: unknown[]) => mockLoginStarted(...args),
    loginSuccess: (...args: unknown[]) => mockLoginSuccess(...args),
    loginError: (...args: unknown[]) => mockLoginError(...args),
    registerStarted: vi.fn(),
    registerSuccess: vi.fn(),
    registerError: vi.fn(),
    logout: (...args: unknown[]) => mockAnalyticsLogout(...args),
    sessionRestored: (...args: unknown[]) => mockSessionRestored(...args),
    sessionExpired: vi.fn(),
    telegramStarted: (...args: unknown[]) => mockTelegramStarted(...args),
    telegramSuccess: (...args: unknown[]) => mockTelegramSuccess(...args),
    telegramError: (...args: unknown[]) => mockTelegramError(...args),
    rateLimited: (...args: unknown[]) => mockRateLimited(...args),
  },
}));

// Import AFTER mocks are set up
import { useAuthStore } from '../auth-store';

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

function createMockMiniAppUser(overrides: Record<string, unknown> = {}) {
  return {
    id: 'usr_miniapp_001',
    login: 'miniapp_user',
    email: 'miniapp@cybervpn.io',
    is_active: true,
    is_email_verified: true,
    created_at: '2025-06-01T12:00:00Z',
    ...overrides,
  };
}

function createMockMiniAppResponse(overrides: Record<string, unknown> = {}) {
  return {
    access_token: 'miniapp_access_token',
    refresh_token: 'miniapp_refresh_token',
    token_type: 'bearer',
    expires_in: 3600,
    user: createMockMiniAppUser(),
    is_new_user: false,
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

function setupTelegramWebApp() {
  Object.defineProperty(window, 'Telegram', {
    value: {
      WebApp: {
        initData: 'query_id=test123&user=mock_user',
      },
    },
    writable: true,
    configurable: true,
  });
}

function teardownTelegramWebApp() {
  Object.defineProperty(window, 'Telegram', {
    value: undefined,
    writable: true,
    configurable: true,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Auth Store - telegramMiniAppAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStoreState();
    setupTelegramWebApp();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    teardownTelegramWebApp();
  });

  // =========================================================================
  // Success path
  // =========================================================================

  it('test_telegramMiniAppAuth_success_sets_authenticated_user', async () => {
    // Arrange
    const mockUser = createMockMiniAppUser({ id: 'usr_ma_success' });
    mockTelegramMiniApp.mockResolvedValue({
      data: createMockMiniAppResponse({ user: mockUser }),
    });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.id).toBe('usr_ma_success');
    expect(state.isLoading).toBe(false);
    expect(state.error).toBe(null);
  });

  it('test_telegramMiniAppAuth_success_stores_tokens', async () => {
    // Arrange
    mockTelegramMiniApp.mockResolvedValue({
      data: createMockMiniAppResponse({
        access_token: 'ma_at_123',
        refresh_token: 'ma_rt_456',
      }),
    });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert
    expect(mockSetTokens).toHaveBeenCalledWith('ma_at_123', 'ma_rt_456');
  });

  it('test_telegramMiniAppAuth_success_passes_initData_to_api', async () => {
    // Arrange
    mockTelegramMiniApp.mockResolvedValue({
      data: createMockMiniAppResponse(),
    });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert
    expect(mockTelegramMiniApp).toHaveBeenCalledWith('query_id=test123&user=mock_user');
  });

  it('test_telegramMiniAppAuth_success_calls_analytics', async () => {
    // Arrange
    const mockUser = createMockMiniAppUser({ id: 'ma_analytics_user' });
    mockTelegramMiniApp.mockResolvedValue({
      data: createMockMiniAppResponse({ user: mockUser }),
    });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert
    expect(mockTelegramStarted).toHaveBeenCalledOnce();
    expect(mockTelegramSuccess).toHaveBeenCalledWith('ma_analytics_user');
  });

  it('test_telegramMiniAppAuth_new_user_sets_isNewTelegramUser_flag', async () => {
    // Arrange
    mockTelegramMiniApp.mockResolvedValue({
      data: createMockMiniAppResponse({ is_new_user: true }),
    });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert
    expect(useAuthStore.getState().isNewTelegramUser).toBe(true);
  });

  it('test_telegramMiniAppAuth_existing_user_sets_isNewTelegramUser_false', async () => {
    // Arrange
    mockTelegramMiniApp.mockResolvedValue({
      data: createMockMiniAppResponse({ is_new_user: false }),
    });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert
    expect(useAuthStore.getState().isNewTelegramUser).toBe(false);
  });

  it('test_telegramMiniAppAuth_missing_is_new_user_defaults_to_false', async () => {
    // Arrange
    const response = createMockMiniAppResponse();
    delete (response as Record<string, unknown>).is_new_user;
    mockTelegramMiniApp.mockResolvedValue({ data: response });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert
    expect(useAuthStore.getState().isNewTelegramUser).toBe(false);
  });

  it('test_telegramMiniAppAuth_user_with_null_email_coerces_to_empty_string', async () => {
    // Arrange - Telegram users may not have email
    const mockUser = createMockMiniAppUser({ email: null });
    mockTelegramMiniApp.mockResolvedValue({
      data: createMockMiniAppResponse({ user: mockUser }),
    });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert
    expect(useAuthStore.getState().user?.email).toBe('');
  });

  it('test_telegramMiniAppAuth_sets_loading_during_request', async () => {
    // Arrange
    let resolvePromise: (v: unknown) => void;
    const deferred = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    mockTelegramMiniApp.mockReturnValue(deferred);

    // Act
    const promise = useAuthStore.getState().telegramMiniAppAuth();

    // Assert - should be loading
    expect(useAuthStore.getState().isLoading).toBe(true);
    expect(useAuthStore.getState().error).toBe(null);

    // Cleanup
    resolvePromise!({ data: createMockMiniAppResponse() });
    await promise;
    expect(useAuthStore.getState().isLoading).toBe(false);
  });

  // =========================================================================
  // Environment guard
  // =========================================================================

  it('test_telegramMiniAppAuth_throws_when_not_in_miniapp_context', async () => {
    // Arrange - remove Telegram from window
    teardownTelegramWebApp();

    // Act & Assert
    await expect(
      useAuthStore.getState().telegramMiniAppAuth()
    ).rejects.toThrow('Not in Telegram Mini App context');

    // API should NOT have been called
    expect(mockTelegramMiniApp).not.toHaveBeenCalled();
  });

  it('test_telegramMiniAppAuth_throws_when_webApp_is_missing', async () => {
    // Arrange - Telegram object exists but WebApp is missing
    Object.defineProperty(window, 'Telegram', {
      value: {},
      writable: true,
      configurable: true,
    });

    // Act & Assert
    await expect(
      useAuthStore.getState().telegramMiniAppAuth()
    ).rejects.toThrow('Not in Telegram Mini App context');
  });

  // =========================================================================
  // Retry logic (1 retry on failure)
  // Uses real timers to avoid unhandled rejection issues with fake timers.
  // The retry delay is 500ms which is acceptable for tests.
  // =========================================================================

  it('test_telegramMiniAppAuth_retries_once_on_first_failure_then_succeeds', async () => {
    // Arrange - first call fails, second call succeeds
    const successResponse = createMockMiniAppResponse({
      user: createMockMiniAppUser({ id: 'retry_success' }),
    });
    mockTelegramMiniApp
      .mockRejectedValueOnce(new Error('Temporary failure'))
      .mockResolvedValueOnce({ data: successResponse });

    // Act - await the full retry flow (500ms delay + two API calls)
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert
    expect(mockTelegramMiniApp).toHaveBeenCalledTimes(2);
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.id).toBe('retry_success');
    expect(state.error).toBe(null);
  });

  it('test_telegramMiniAppAuth_fails_after_both_attempts_exhausted', async () => {
    // Arrange - both attempts fail
    mockTelegramMiniApp
      .mockRejectedValueOnce(new Error('Attempt 1 failed'))
      .mockRejectedValueOnce({
        response: { data: { detail: 'Server unavailable' } },
      });

    // Act & Assert
    await expect(
      useAuthStore.getState().telegramMiniAppAuth()
    ).rejects.toBeDefined();

    // Assert
    expect(mockTelegramMiniApp).toHaveBeenCalledTimes(2);
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.error).toBe('Server unavailable');
    expect(state.isLoading).toBe(false);
  });

  it('test_telegramMiniAppAuth_uses_fallback_error_when_no_detail', async () => {
    // Arrange - both attempts fail with generic error (no response.data.detail)
    mockTelegramMiniApp
      .mockRejectedValueOnce(new Error('Network error'))
      .mockRejectedValueOnce(new Error('Network error again'));

    // Act & Assert
    await expect(
      useAuthStore.getState().telegramMiniAppAuth()
    ).rejects.toBeDefined();

    // Assert
    expect(useAuthStore.getState().error).toBe('Telegram Mini App auth failed');
  });

  it('test_telegramMiniAppAuth_calls_analytics_error_on_final_failure', async () => {
    // Arrange
    mockTelegramMiniApp
      .mockRejectedValueOnce(new Error('fail1'))
      .mockRejectedValueOnce({
        response: { data: { detail: 'Auth validation error' } },
      });

    // Act
    await expect(
      useAuthStore.getState().telegramMiniAppAuth()
    ).rejects.toBeDefined();

    // Assert
    expect(mockTelegramError).toHaveBeenCalledWith('Auth validation error');
  });

  it('test_telegramMiniAppAuth_does_not_retry_on_first_success', async () => {
    // Arrange
    mockTelegramMiniApp.mockResolvedValue({
      data: createMockMiniAppResponse(),
    });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert - only called once, no retry
    expect(mockTelegramMiniApp).toHaveBeenCalledTimes(1);
  });

  it('test_telegramMiniAppAuth_calls_api_exactly_twice_on_retry', async () => {
    // Arrange - first fails, second succeeds
    mockTelegramMiniApp
      .mockRejectedValueOnce(new Error('First attempt'))
      .mockResolvedValueOnce({ data: createMockMiniAppResponse() });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert - should have retried exactly once (2 total calls)
    expect(mockTelegramMiniApp).toHaveBeenCalledTimes(2);
    // Both calls should use the same initData
    expect(mockTelegramMiniApp).toHaveBeenNthCalledWith(1, 'query_id=test123&user=mock_user');
    expect(mockTelegramMiniApp).toHaveBeenNthCalledWith(2, 'query_id=test123&user=mock_user');
  });

  // =========================================================================
  // User data mapping
  // =========================================================================

  it('test_telegramMiniAppAuth_maps_user_fields_correctly', async () => {
    // Arrange
    const mockUser = {
      id: 'usr_field_mapping',
      login: 'test_login',
      email: 'mapped@test.com',
      is_active: true,
      is_email_verified: false,
      created_at: '2025-03-15T10:30:00Z',
    };
    mockTelegramMiniApp.mockResolvedValue({
      data: createMockMiniAppResponse({ user: mockUser }),
    });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert - the store maps specific fields and sets role to 'viewer'
    const user = useAuthStore.getState().user;
    expect(user).toEqual({
      id: 'usr_field_mapping',
      login: 'test_login',
      email: 'mapped@test.com',
      is_active: true,
      is_email_verified: false,
      role: 'viewer',
      created_at: '2025-03-15T10:30:00Z',
    });
  });

  it('test_telegramMiniAppAuth_sets_role_to_viewer_regardless_of_api_response', async () => {
    // Arrange - even if the user has a different role in the API response,
    // the store hardcodes 'viewer' for mini-app auth
    const mockUser = createMockMiniAppUser({ role: 'admin' });
    mockTelegramMiniApp.mockResolvedValue({
      data: createMockMiniAppResponse({ user: mockUser }),
    });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert
    expect(useAuthStore.getState().user?.role).toBe('viewer');
  });

  // =========================================================================
  // Edge cases
  // =========================================================================

  it('test_telegramMiniAppAuth_clears_previous_error_on_start', async () => {
    // Arrange
    useAuthStore.setState({ error: 'previous error from another action' });
    mockTelegramMiniApp.mockResolvedValue({
      data: createMockMiniAppResponse(),
    });

    // Act
    await useAuthStore.getState().telegramMiniAppAuth();

    // Assert
    expect(useAuthStore.getState().error).toBe(null);
  });

  it('test_telegramMiniAppAuth_does_not_call_analytics_started_when_not_in_context', async () => {
    // Arrange - remove Telegram context
    teardownTelegramWebApp();

    // Act
    await useAuthStore.getState().telegramMiniAppAuth().catch(() => {
      // Expected to throw
    });

    // Assert - telegramStarted should NOT have been called because
    // the guard throws before set() and analytics calls
    expect(mockTelegramStarted).not.toHaveBeenCalled();
  });
});
