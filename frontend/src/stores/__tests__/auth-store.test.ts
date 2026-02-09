import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Use vi.hoisted() so these mock functions are available when vi.mock factories run
const {
  mockLogin,
  mockRegister,
  mockVerifyOtp,
  mockLogout,
  mockMe,
  mockTelegramWidget,
  mockTelegramMiniApp,
  mockTelegramBotLink,
  mockOauthLoginAuthorize,
  mockOauthLoginCallback,
  mockRequestMagicLink,
  mockVerifyMagicLink,
  mockDeleteAccount,
  mockSetTokens,
  mockClearTokens,
  MockRateLimitError,
  mockLoginStarted,
  mockLoginSuccess,
  mockLoginError,
  mockRegisterStarted,
  mockRegisterSuccess,
  mockRegisterError,
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
    mockLogin: vi.fn(),
    mockRegister: vi.fn(),
    mockVerifyOtp: vi.fn(),
    mockLogout: vi.fn(),
    mockMe: vi.fn(),
    mockTelegramWidget: vi.fn(),
    mockTelegramMiniApp: vi.fn(),
    mockTelegramBotLink: vi.fn(),
    mockOauthLoginAuthorize: vi.fn(),
    mockOauthLoginCallback: vi.fn(),
    mockRequestMagicLink: vi.fn(),
    mockVerifyMagicLink: vi.fn(),
    mockDeleteAccount: vi.fn(),
    mockSetTokens: vi.fn(),
    mockClearTokens: vi.fn(),
    MockRateLimitError: _RateLimitError,
    mockLoginStarted: vi.fn(),
    mockLoginSuccess: vi.fn(),
    mockLoginError: vi.fn(),
    mockRegisterStarted: vi.fn(),
    mockRegisterSuccess: vi.fn(),
    mockRegisterError: vi.fn(),
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
    login: (...args: unknown[]) => mockLogin(...args),
    register: (...args: unknown[]) => mockRegister(...args),
    verifyOtp: (...args: unknown[]) => mockVerifyOtp(...args),
    logout: (...args: unknown[]) => mockLogout(...args),
    me: (...args: unknown[]) => mockMe(...args),
    telegramWidget: (...args: unknown[]) => mockTelegramWidget(...args),
    telegramMiniApp: (...args: unknown[]) => mockTelegramMiniApp(...args),
    telegramBotLink: (...args: unknown[]) => mockTelegramBotLink(...args),
    oauthLoginAuthorize: (...args: unknown[]) => mockOauthLoginAuthorize(...args),
    oauthLoginCallback: (...args: unknown[]) => mockOauthLoginCallback(...args),
    requestMagicLink: (...args: unknown[]) => mockRequestMagicLink(...args),
    verifyMagicLink: (...args: unknown[]) => mockVerifyMagicLink(...args),
    deleteAccount: (...args: unknown[]) => mockDeleteAccount(...args),
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
    registerStarted: (...args: unknown[]) => mockRegisterStarted(...args),
    registerSuccess: (...args: unknown[]) => mockRegisterSuccess(...args),
    registerError: (...args: unknown[]) => mockRegisterError(...args),
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

function createMockUser(overrides: Record<string, unknown> = {}) {
  return {
    id: 'usr_test_001',
    email: 'testuser@cybervpn.io',
    login: 'testuser',
    role: 'user' as const,
    is_active: true,
    is_email_verified: true,
    created_at: '2025-06-01T12:00:00Z',
    ...overrides,
  };
}

function createMockTokenResponse(overrides: Record<string, unknown> = {}) {
  return {
    access_token: 'mock_access_token_abc123',
    refresh_token: 'mock_refresh_token_xyz789',
    token_type: 'bearer',
    expires_in: 3600,
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

describe('Auth Store', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStoreState();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // =========================================================================
  // Initial state
  // =========================================================================

  describe('initial state', () => {
    it('test_initial_state_user_is_null', () => {
      const state = useAuthStore.getState();
      expect(state.user).toBe(null);
    });

    it('test_initial_state_isLoading_is_false', () => {
      const state = useAuthStore.getState();
      expect(state.isLoading).toBe(false);
    });

    it('test_initial_state_isAuthenticated_is_false', () => {
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
    });

    it('test_initial_state_isNewTelegramUser_is_false', () => {
      const state = useAuthStore.getState();
      expect(state.isNewTelegramUser).toBe(false);
    });

    it('test_initial_state_error_is_null', () => {
      const state = useAuthStore.getState();
      expect(state.error).toBe(null);
    });

    it('test_initial_state_rateLimitUntil_is_null', () => {
      const state = useAuthStore.getState();
      expect(state.rateLimitUntil).toBe(null);
    });

    it('test_initial_state_has_all_action_methods', () => {
      const state = useAuthStore.getState();
      expect(typeof state.login).toBe('function');
      expect(typeof state.register).toBe('function');
      expect(typeof state.verifyOtpAndLogin).toBe('function');
      expect(typeof state.logout).toBe('function');
      expect(typeof state.fetchUser).toBe('function');
      expect(typeof state.telegramAuth).toBe('function');
      expect(typeof state.telegramMiniAppAuth).toBe('function');
      expect(typeof state.loginWithBotLink).toBe('function');
      expect(typeof state.oauthLogin).toBe('function');
      expect(typeof state.oauthCallback).toBe('function');
      expect(typeof state.requestMagicLink).toBe('function');
      expect(typeof state.verifyMagicLink).toBe('function');
      expect(typeof state.deleteAccount).toBe('function');
      expect(typeof state.clearError).toBe('function');
      expect(typeof state.clearRateLimit).toBe('function');
    });
  });

  // =========================================================================
  // login
  // =========================================================================

  describe('login', () => {
    it('test_login_success_sets_authenticated_user', async () => {
      // Arrange
      const mockUser = createMockUser();
      const mockTokens = createMockTokenResponse();
      mockLogin.mockResolvedValue({ data: mockTokens });
      mockMe.mockResolvedValue({ data: mockUser });

      // Act
      await useAuthStore.getState().login('testuser@cybervpn.io', 'correct_password');

      // Assert
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user).toEqual(mockUser);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe(null);
    });

    it('test_login_success_stores_tokens', async () => {
      // Arrange
      mockLogin.mockResolvedValue({
        data: createMockTokenResponse({
          access_token: 'at_login',
          refresh_token: 'rt_login',
        }),
      });
      mockMe.mockResolvedValue({ data: createMockUser() });

      // Act
      await useAuthStore.getState().login('test@test.com', 'password');

      // Assert
      expect(mockSetTokens).toHaveBeenCalledWith('at_login', 'rt_login');
    });

    it('test_login_success_calls_analytics', async () => {
      // Arrange
      const mockUser = createMockUser({ id: 'user_analytics_test' });
      mockLogin.mockResolvedValue({ data: createMockTokenResponse() });
      mockMe.mockResolvedValue({ data: mockUser });

      // Act
      await useAuthStore.getState().login('test@test.com', 'pw');

      // Assert
      expect(mockLoginStarted).toHaveBeenCalledOnce();
      expect(mockLoginSuccess).toHaveBeenCalledWith('user_analytics_test', 'email');
    });

    it('test_login_sets_loading_during_request', async () => {
      // Arrange
      let resolveLogin: (v: unknown) => void;
      const deferred = new Promise((resolve) => { resolveLogin = resolve; });
      mockLogin.mockReturnValue(deferred);

      // Act
      const promise = useAuthStore.getState().login('e@e.com', 'p');

      // Assert - should be loading
      expect(useAuthStore.getState().isLoading).toBe(true);
      expect(useAuthStore.getState().error).toBe(null);

      // Cleanup
      mockMe.mockResolvedValue({ data: createMockUser() });
      resolveLogin!({ data: createMockTokenResponse() });
      await promise;
    });

    it('test_login_clears_previous_error_on_start', async () => {
      // Arrange
      useAuthStore.setState({ error: 'previous error', rateLimitUntil: 99999 });
      mockLogin.mockResolvedValue({ data: createMockTokenResponse() });
      mockMe.mockResolvedValue({ data: createMockUser() });

      // Act
      await useAuthStore.getState().login('e@e.com', 'p');

      // Assert
      expect(useAuthStore.getState().error).toBe(null);
      expect(useAuthStore.getState().rateLimitUntil).toBe(null);
    });

    it('test_login_failure_sets_error_message', async () => {
      // Arrange
      mockLogin.mockRejectedValue({
        response: { data: { detail: 'Invalid email or password' } },
      });

      // Act & Assert
      await expect(
        useAuthStore.getState().login('bad@test.com', 'wrong')
      ).rejects.toBeDefined();

      const state = useAuthStore.getState();
      expect(state.error).toBe('Invalid email or password');
      expect(state.isLoading).toBe(false);
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBe(null);
    });

    it('test_login_failure_uses_fallback_error_message', async () => {
      // Arrange
      mockLogin.mockRejectedValue(new Error('Network error'));

      // Act & Assert
      await expect(
        useAuthStore.getState().login('e@e.com', 'p')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Login failed');
    });

    it('test_login_failure_calls_analytics_error', async () => {
      // Arrange
      mockLogin.mockRejectedValue({
        response: { data: { detail: 'Account is disabled' } },
      });

      // Act
      await expect(
        useAuthStore.getState().login('banned@test.com', 'pw')
      ).rejects.toBeDefined();

      // Assert
      expect(mockLoginError).toHaveBeenCalledWith('Account is disabled');
    });

    it('test_login_rate_limit_sets_rateLimitUntil', async () => {
      // Arrange
      const rateLimitErr = new MockRateLimitError(30);
      mockLogin.mockRejectedValue(rateLimitErr);
      const beforeTime = Date.now();

      // Act
      await expect(
        useAuthStore.getState().login('e@e.com', 'p')
      ).rejects.toBeDefined();

      // Assert
      const state = useAuthStore.getState();
      expect(state.rateLimitUntil).toBeGreaterThanOrEqual(beforeTime + 30000);
      expect(state.isLoading).toBe(false);
      expect(mockRateLimited).toHaveBeenCalledWith(30);
    });

    it('test_login_with_rememberMe_passes_flag_to_api', async () => {
      // Arrange
      mockLogin.mockResolvedValue({ data: createMockTokenResponse() });
      mockMe.mockResolvedValue({ data: createMockUser() });

      // Act
      await useAuthStore.getState().login('e@e.com', 'p', true);

      // Assert
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'e@e.com',
        password: 'p',
        remember_me: true,
      });
    });
  });

  // =========================================================================
  // register
  // =========================================================================

  describe('register', () => {
    it('test_register_success_sets_user_not_authenticated', async () => {
      // Arrange
      mockRegister.mockResolvedValue({
        data: {
          id: 'usr_new_001',
          login: 'newuser',
          email: 'new@cybervpn.io',
          is_active: false,
          is_email_verified: false,
          message: 'Registration successful.',
        },
      });

      // Act
      await useAuthStore.getState().register('new@cybervpn.io', 'securePass123');

      // Assert
      const state = useAuthStore.getState();
      expect(state.user).toBeTruthy();
      expect(state.user?.id).toBe('usr_new_001');
      expect(state.user?.email).toBe('new@cybervpn.io');
      expect(state.user?.is_active).toBe(false);
      expect(state.user?.is_email_verified).toBe(false);
      // NOT authenticated until OTP verification
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
    });

    it('test_register_derives_login_from_email', async () => {
      // Arrange
      mockRegister.mockResolvedValue({
        data: {
          id: 'usr_new_002',
          login: 'john.doe',
          email: 'john.doe@example.com',
          is_active: false,
          is_email_verified: false,
        },
      });

      // Act
      await useAuthStore.getState().register('john.doe@example.com', 'pass');

      // Assert
      expect(mockRegister).toHaveBeenCalledWith({
        login: 'john.doe',
        email: 'john.doe@example.com',
        password: 'pass',
      });
    });

    it('test_register_success_calls_analytics', async () => {
      // Arrange
      mockRegister.mockResolvedValue({
        data: {
          id: 'usr_analytics_reg',
          login: 'user',
          email: 'user@e.com',
          is_active: false,
          is_email_verified: false,
        },
      });

      // Act
      await useAuthStore.getState().register('user@e.com', 'pass');

      // Assert
      expect(mockRegisterStarted).toHaveBeenCalledOnce();
      expect(mockRegisterSuccess).toHaveBeenCalledWith('usr_analytics_reg');
    });

    it('test_register_failure_sets_error', async () => {
      // Arrange
      mockRegister.mockRejectedValue({
        response: { data: { detail: 'Email already registered' } },
      });

      // Act & Assert
      await expect(
        useAuthStore.getState().register('taken@cybervpn.io', 'pass')
      ).rejects.toBeDefined();

      const state = useAuthStore.getState();
      expect(state.error).toBe('Email already registered');
      expect(state.isLoading).toBe(false);
    });

    it('test_register_failure_uses_fallback_error', async () => {
      // Arrange
      mockRegister.mockRejectedValue(new Error('Network failure'));

      // Act & Assert
      await expect(
        useAuthStore.getState().register('e@e.com', 'p')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Registration failed');
    });

    it('test_register_failure_calls_analytics_error', async () => {
      // Arrange
      mockRegister.mockRejectedValue({
        response: { data: { detail: 'Email already registered' } },
      });

      // Act
      await expect(
        useAuthStore.getState().register('taken@e.com', 'p')
      ).rejects.toBeDefined();

      // Assert
      expect(mockRegisterError).toHaveBeenCalledWith('Email already registered');
    });

    it('test_register_rate_limit_sets_rateLimitUntil', async () => {
      // Arrange
      const rateLimitErr = new MockRateLimitError(60);
      mockRegister.mockRejectedValue(rateLimitErr);

      // Act
      await expect(
        useAuthStore.getState().register('e@e.com', 'p')
      ).rejects.toBeDefined();

      // Assert
      const state = useAuthStore.getState();
      expect(state.rateLimitUntil).toBeTruthy();
      expect(state.rateLimitUntil).toBeGreaterThan(Date.now());
      expect(mockRateLimited).toHaveBeenCalledWith(60);
    });
  });

  // =========================================================================
  // verifyOtpAndLogin
  // =========================================================================

  describe('verifyOtpAndLogin', () => {
    it('test_verifyOtp_success_sets_authenticated_user_with_tokens', async () => {
      // Arrange
      const mockUser = createMockUser({ id: 'usr_otp_001', role: 'user' });
      mockVerifyOtp.mockResolvedValue({
        data: {
          ...createMockTokenResponse({
            access_token: 'otp_access',
            refresh_token: 'otp_refresh',
          }),
          user: mockUser,
        },
      });

      // Act
      await useAuthStore.getState().verifyOtpAndLogin('test@test.com', '123456');

      // Assert
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user?.id).toBe('usr_otp_001');
      expect(state.isLoading).toBe(false);
      expect(mockSetTokens).toHaveBeenCalledWith('otp_access', 'otp_refresh');
    });

    it('test_verifyOtp_calls_api_with_email_and_code', async () => {
      // Arrange
      mockVerifyOtp.mockResolvedValue({
        data: {
          ...createMockTokenResponse(),
          user: createMockUser(),
        },
      });

      // Act
      await useAuthStore.getState().verifyOtpAndLogin('user@example.com', '654321');

      // Assert
      expect(mockVerifyOtp).toHaveBeenCalledWith({
        email: 'user@example.com',
        code: '654321',
      });
    });

    it('test_verifyOtp_success_calls_login_analytics', async () => {
      // Arrange
      const mockUser = createMockUser({ id: 'usr_otp_analytics' });
      mockVerifyOtp.mockResolvedValue({
        data: { ...createMockTokenResponse(), user: mockUser },
      });

      // Act
      await useAuthStore.getState().verifyOtpAndLogin('e@e.com', '111111');

      // Assert
      expect(mockLoginSuccess).toHaveBeenCalledWith('usr_otp_analytics', 'email');
    });

    it('test_verifyOtp_failure_sets_error_from_string_detail', async () => {
      // Arrange
      mockVerifyOtp.mockRejectedValue({
        response: { data: { detail: 'Invalid or expired OTP code' } },
      });

      // Act & Assert
      await expect(
        useAuthStore.getState().verifyOtpAndLogin('e@e.com', '000000')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Invalid or expired OTP code');
      expect(useAuthStore.getState().isLoading).toBe(false);
    });

    it('test_verifyOtp_failure_sets_error_from_nested_detail', async () => {
      // Arrange - the store has special handling for { detail: { detail: "..." } }
      mockVerifyOtp.mockRejectedValue({
        response: { data: { detail: { detail: 'Nested error message' } } },
      });

      // Act & Assert
      await expect(
        useAuthStore.getState().verifyOtpAndLogin('e@e.com', 'bad')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Nested error message');
    });

    it('test_verifyOtp_failure_uses_fallback_error', async () => {
      // Arrange
      mockVerifyOtp.mockRejectedValue(new Error('Network error'));

      // Act & Assert
      await expect(
        useAuthStore.getState().verifyOtpAndLogin('e@e.com', '000')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Verification failed');
    });

    it('test_verifyOtp_sets_loading_during_request', async () => {
      // Arrange
      let resolvePromise: (v: unknown) => void;
      const deferred = new Promise((resolve) => { resolvePromise = resolve; });
      mockVerifyOtp.mockReturnValue(deferred);

      // Act
      const promise = useAuthStore.getState().verifyOtpAndLogin('e@e.com', '123');

      // Assert
      expect(useAuthStore.getState().isLoading).toBe(true);

      // Cleanup
      resolvePromise!({
        data: { ...createMockTokenResponse(), user: createMockUser() },
      });
      await promise;
      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });

  // =========================================================================
  // logout
  // =========================================================================

  describe('logout', () => {
    it('test_logout_clears_user_and_auth_state', async () => {
      // Arrange
      useAuthStore.setState({
        user: createMockUser(),
        isAuthenticated: true,
        isNewTelegramUser: true,
        error: 'stale error',
      });
      mockLogout.mockResolvedValue({ data: { message: 'Logged out' } });

      // Act
      await useAuthStore.getState().logout();

      // Assert
      const state = useAuthStore.getState();
      expect(state.user).toBe(null);
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe(null);
      expect(state.isNewTelegramUser).toBe(false);
    });

    it('test_logout_clears_tokens', async () => {
      // Arrange
      useAuthStore.setState({ user: createMockUser(), isAuthenticated: true });
      mockLogout.mockResolvedValue({ data: {} });

      // Act
      await useAuthStore.getState().logout();

      // Assert
      expect(mockClearTokens).toHaveBeenCalledOnce();
    });

    it('test_logout_calls_analytics', async () => {
      // Arrange
      useAuthStore.setState({ user: createMockUser(), isAuthenticated: true });
      mockLogout.mockResolvedValue({ data: {} });

      // Act
      await useAuthStore.getState().logout();

      // Assert
      expect(mockAnalyticsLogout).toHaveBeenCalledOnce();
    });

    it('test_logout_clears_state_even_when_api_fails', async () => {
      // Arrange - the store uses try/finally so state should be cleared on failure too
      useAuthStore.setState({ user: createMockUser(), isAuthenticated: true });
      mockLogout.mockRejectedValue(new Error('Network error'));

      // Act - logout uses try/finally without catch, so the error propagates
      // but the finally block still clears state
      await useAuthStore.getState().logout().catch(() => {
        // Expected: the rejected promise from authApi.logout() bubbles up
      });

      // Assert - state is cleared despite error (finally block)
      const state = useAuthStore.getState();
      expect(state.user).toBe(null);
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(mockClearTokens).toHaveBeenCalledOnce();
    });
  });

  // =========================================================================
  // fetchUser
  // =========================================================================

  describe('fetchUser', () => {
    it('test_fetchUser_success_sets_user_and_authenticated', async () => {
      // Arrange
      const mockUser = createMockUser({ id: 'usr_fetch_001' });
      mockMe.mockResolvedValue({ data: mockUser });

      // Act
      await useAuthStore.getState().fetchUser();

      // Assert
      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isLoading).toBe(false);
    });

    it('test_fetchUser_success_calls_sessionRestored_analytics', async () => {
      // Arrange
      const mockUser = createMockUser({ id: 'usr_session' });
      mockMe.mockResolvedValue({ data: mockUser });

      // Act
      await useAuthStore.getState().fetchUser();

      // Assert
      expect(mockSessionRestored).toHaveBeenCalledWith('usr_session');
    });

    it('test_fetchUser_failure_clears_auth_state', async () => {
      // Arrange
      useAuthStore.setState({
        user: createMockUser(),
        isAuthenticated: true,
      });
      mockMe.mockRejectedValue(new Error('Unauthorized'));

      // Act
      await useAuthStore.getState().fetchUser();

      // Assert
      const state = useAuthStore.getState();
      expect(state.user).toBe(null);
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
    });

    it('test_fetchUser_failure_does_not_throw', async () => {
      // Arrange
      mockMe.mockRejectedValue(new Error('Server error'));

      // Act & Assert - should NOT throw, handled silently
      await expect(useAuthStore.getState().fetchUser()).resolves.toBeUndefined();
    });

    it('test_fetchUser_sets_loading_during_request', async () => {
      // Arrange
      let resolvePromise: (v: unknown) => void;
      const deferred = new Promise((resolve) => { resolvePromise = resolve; });
      mockMe.mockReturnValue(deferred);

      // Act
      const promise = useAuthStore.getState().fetchUser();

      // Assert
      expect(useAuthStore.getState().isLoading).toBe(true);

      // Cleanup
      resolvePromise!({ data: createMockUser() });
      await promise;
    });
  });

  // =========================================================================
  // telegramAuth
  // =========================================================================

  describe('telegramAuth', () => {
    const widgetData = {
      id: 123456789,
      first_name: 'Test',
      auth_date: 1700000000,
      hash: 'abc123hash',
    };

    it('test_telegramAuth_success_sets_authenticated_user', async () => {
      // Arrange
      const mockUser = createMockUser({ id: 'usr_tg_001', telegram_id: 123456789 });
      mockTelegramWidget.mockResolvedValue({
        data: { user: mockUser, is_new_user: false },
      });

      // Act
      await useAuthStore.getState().telegramAuth(widgetData);

      // Assert
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user).toEqual(mockUser);
      expect(state.isNewTelegramUser).toBe(false);
      expect(state.isLoading).toBe(false);
    });

    it('test_telegramAuth_new_user_sets_isNewTelegramUser_flag', async () => {
      // Arrange
      mockTelegramWidget.mockResolvedValue({
        data: { user: createMockUser(), is_new_user: true },
      });

      // Act
      await useAuthStore.getState().telegramAuth(widgetData);

      // Assert
      expect(useAuthStore.getState().isNewTelegramUser).toBe(true);
    });

    it('test_telegramAuth_missing_is_new_user_defaults_to_false', async () => {
      // Arrange - is_new_user not in response
      mockTelegramWidget.mockResolvedValue({
        data: { user: createMockUser() },
      });

      // Act
      await useAuthStore.getState().telegramAuth(widgetData);

      // Assert
      expect(useAuthStore.getState().isNewTelegramUser).toBe(false);
    });

    it('test_telegramAuth_calls_analytics', async () => {
      // Arrange
      const mockUser = createMockUser({ id: 'tg_analytics' });
      mockTelegramWidget.mockResolvedValue({
        data: { user: mockUser, is_new_user: false },
      });

      // Act
      await useAuthStore.getState().telegramAuth(widgetData);

      // Assert
      expect(mockTelegramStarted).toHaveBeenCalledOnce();
      expect(mockTelegramSuccess).toHaveBeenCalledWith('tg_analytics');
    });

    it('test_telegramAuth_failure_sets_error', async () => {
      // Arrange
      mockTelegramWidget.mockRejectedValue({
        response: { data: { detail: 'Telegram auth failed' } },
      });

      // Act & Assert
      await expect(
        useAuthStore.getState().telegramAuth(widgetData)
      ).rejects.toBeDefined();

      const state = useAuthStore.getState();
      expect(state.error).toBe('Telegram auth failed');
      expect(state.isLoading).toBe(false);
    });

    it('test_telegramAuth_failure_uses_fallback_error', async () => {
      // Arrange
      mockTelegramWidget.mockRejectedValue(new Error('Network error'));

      // Act & Assert
      await expect(
        useAuthStore.getState().telegramAuth(widgetData)
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Telegram auth failed');
    });

    it('test_telegramAuth_failure_calls_analytics_error', async () => {
      // Arrange
      mockTelegramWidget.mockRejectedValue({
        response: { data: { detail: 'Hash mismatch' } },
      });

      // Act
      await expect(
        useAuthStore.getState().telegramAuth(widgetData)
      ).rejects.toBeDefined();

      // Assert
      expect(mockTelegramError).toHaveBeenCalledWith('Hash mismatch');
    });

    it('test_telegramAuth_resets_isNewTelegramUser_on_start', async () => {
      // Arrange
      useAuthStore.setState({ isNewTelegramUser: true });
      mockTelegramWidget.mockResolvedValue({
        data: { user: createMockUser(), is_new_user: false },
      });

      // Act
      await useAuthStore.getState().telegramAuth(widgetData);

      // Assert
      expect(useAuthStore.getState().isNewTelegramUser).toBe(false);
    });
  });

  // =========================================================================
  // loginWithBotLink
  // =========================================================================

  describe('loginWithBotLink', () => {
    it('test_loginWithBotLink_success_sets_authenticated_user', async () => {
      // Arrange
      mockTelegramBotLink.mockResolvedValue({
        data: {
          access_token: 'bot_access',
          refresh_token: 'bot_refresh',
          token_type: 'bearer',
          expires_in: 3600,
          user: {
            id: 'usr_bot_001',
            login: 'botuser',
            email: 'bot@test.com',
            is_active: true,
            is_email_verified: true,
            created_at: '2025-01-01',
          },
        },
      });

      // Act
      await useAuthStore.getState().loginWithBotLink('valid_bot_token');

      // Assert
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user?.id).toBe('usr_bot_001');
      expect(state.user?.email).toBe('bot@test.com');
      expect(state.isLoading).toBe(false);
      expect(mockSetTokens).toHaveBeenCalledWith('bot_access', 'bot_refresh');
    });

    it('test_loginWithBotLink_passes_token_to_api', async () => {
      // Arrange
      mockTelegramBotLink.mockResolvedValue({
        data: {
          access_token: 'a',
          refresh_token: 'r',
          user: {
            id: 'u1',
            login: 'u',
            email: '',
            is_active: true,
            is_email_verified: false,
            created_at: '2025-01-01',
          },
        },
      });

      // Act
      await useAuthStore.getState().loginWithBotLink('my_token_123');

      // Assert
      expect(mockTelegramBotLink).toHaveBeenCalledWith({ token: 'my_token_123' });
    });

    it('test_loginWithBotLink_calls_login_analytics_with_telegram_method', async () => {
      // Arrange
      mockTelegramBotLink.mockResolvedValue({
        data: {
          access_token: 'a',
          refresh_token: 'r',
          user: {
            id: 'usr_bot_analytics',
            login: 'u',
            email: '',
            is_active: true,
            is_email_verified: false,
            created_at: '2025-01-01',
          },
        },
      });

      // Act
      await useAuthStore.getState().loginWithBotLink('tok');

      // Assert
      expect(mockLoginSuccess).toHaveBeenCalledWith('usr_bot_analytics', 'telegram');
    });

    it('test_loginWithBotLink_failure_sets_error', async () => {
      // Arrange
      mockTelegramBotLink.mockRejectedValue({
        response: { data: { detail: 'Invalid or expired token' } },
      });

      // Act & Assert
      await expect(
        useAuthStore.getState().loginWithBotLink('expired_token')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Invalid or expired token');
      expect(useAuthStore.getState().isLoading).toBe(false);
    });

    it('test_loginWithBotLink_failure_uses_fallback_error', async () => {
      // Arrange
      mockTelegramBotLink.mockRejectedValue(new Error('Network error'));

      // Act & Assert
      await expect(
        useAuthStore.getState().loginWithBotLink('tok')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Bot link login failed');
    });

    it('test_loginWithBotLink_handles_empty_email', async () => {
      // Arrange - Telegram users may not have email
      mockTelegramBotLink.mockResolvedValue({
        data: {
          access_token: 'a',
          refresh_token: 'r',
          user: {
            id: 'usr_noemail',
            login: 'noemail',
            email: null,
            is_active: true,
            is_email_verified: false,
            created_at: '2025-01-01',
          },
        },
      });

      // Act
      await useAuthStore.getState().loginWithBotLink('tok');

      // Assert - null email coerced to empty string via || ''
      expect(useAuthStore.getState().user?.email).toBe('');
    });
  });

  // =========================================================================
  // deleteAccount
  // =========================================================================

  describe('deleteAccount', () => {
    it('test_deleteAccount_success_clears_all_auth_state', async () => {
      // Arrange
      useAuthStore.setState({
        user: createMockUser(),
        isAuthenticated: true,
        isNewTelegramUser: true,
        error: 'old error',
      });
      mockDeleteAccount.mockResolvedValue({ data: { message: 'Account deleted' } });

      // Act
      await useAuthStore.getState().deleteAccount();

      // Assert
      const state = useAuthStore.getState();
      expect(state.user).toBe(null);
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe(null);
      expect(state.isNewTelegramUser).toBe(false);
    });

    it('test_deleteAccount_clears_tokens', async () => {
      // Arrange
      useAuthStore.setState({ user: createMockUser(), isAuthenticated: true });
      mockDeleteAccount.mockResolvedValue({ data: {} });

      // Act
      await useAuthStore.getState().deleteAccount();

      // Assert
      expect(mockClearTokens).toHaveBeenCalledOnce();
    });

    it('test_deleteAccount_calls_logout_analytics', async () => {
      // Arrange
      useAuthStore.setState({ user: createMockUser(), isAuthenticated: true });
      mockDeleteAccount.mockResolvedValue({ data: {} });

      // Act
      await useAuthStore.getState().deleteAccount();

      // Assert
      expect(mockAnalyticsLogout).toHaveBeenCalledOnce();
    });

    it('test_deleteAccount_failure_sets_error', async () => {
      // Arrange
      useAuthStore.setState({ user: createMockUser(), isAuthenticated: true });
      mockDeleteAccount.mockRejectedValue({
        response: { data: { detail: 'Account deletion failed' } },
      });

      // Act & Assert
      await expect(
        useAuthStore.getState().deleteAccount()
      ).rejects.toBeDefined();

      const state = useAuthStore.getState();
      expect(state.error).toBe('Account deletion failed');
      expect(state.isLoading).toBe(false);
      // User should NOT be cleared on failure
      expect(state.user).toBeTruthy();
      expect(state.isAuthenticated).toBe(true);
    });

    it('test_deleteAccount_failure_uses_fallback_error', async () => {
      // Arrange
      useAuthStore.setState({ user: createMockUser(), isAuthenticated: true });
      mockDeleteAccount.mockRejectedValue(new Error('Network'));

      // Act & Assert
      await expect(
        useAuthStore.getState().deleteAccount()
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Account deletion failed');
    });

    it('test_deleteAccount_sets_loading_during_request', async () => {
      // Arrange
      useAuthStore.setState({ user: createMockUser(), isAuthenticated: true });
      let resolvePromise: (v: unknown) => void;
      const deferred = new Promise((resolve) => { resolvePromise = resolve; });
      mockDeleteAccount.mockReturnValue(deferred);

      // Act
      const promise = useAuthStore.getState().deleteAccount();

      // Assert
      expect(useAuthStore.getState().isLoading).toBe(true);

      // Cleanup
      resolvePromise!({ data: {} });
      await promise;
      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });

  // =========================================================================
  // oauthLogin
  // =========================================================================

  describe('oauthLogin', () => {
    it('test_oauthLogin_stores_provider_in_sessionStorage_and_redirects', async () => {
      mockOauthLoginAuthorize.mockResolvedValue({
        data: {
          authorize_url: 'https://accounts.google.com/oauth?state=csrf123',
          state: 'csrf123',
        },
      });

      const store = useAuthStore.getState();
      await store.oauthLogin('google');

      // Should store CSRF state in sessionStorage
      expect(sessionStorage.setItem).toHaveBeenCalledWith('oauth_state', 'csrf123');
      expect(sessionStorage.setItem).toHaveBeenCalledWith('oauth_provider', 'google');

      // Should redirect to the authorization URL
      expect(window.location.href).toBe('https://accounts.google.com/oauth?state=csrf123');
    });

    it('test_oauthLogin_sets_loading_state_during_request', async () => {
      // Create a deferred promise so we can inspect state mid-flight
      let resolvePromise: (value: unknown) => void;
      const deferredPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      mockOauthLoginAuthorize.mockReturnValue(deferredPromise);

      const promise = useAuthStore.getState().oauthLogin('github');

      // Should be loading
      expect(useAuthStore.getState().isLoading).toBe(true);
      expect(useAuthStore.getState().error).toBe(null);

      // Resolve the promise
      resolvePromise!({
        data: {
          authorize_url: 'https://github.com/login/oauth',
          state: 'gh_state',
        },
      });

      await promise;
    });

    it('test_oauthLogin_sets_error_on_failure', async () => {
      mockOauthLoginAuthorize.mockRejectedValue({
        response: { data: { detail: 'Provider not configured' } },
      });

      await expect(
        useAuthStore.getState().oauthLogin('twitter')
      ).rejects.toBeDefined();

      const state = useAuthStore.getState();
      expect(state.error).toBe('Provider not configured');
      expect(state.isLoading).toBe(false);
    });

    it('test_oauthLogin_uses_fallback_error_message', async () => {
      mockOauthLoginAuthorize.mockRejectedValue(new Error('Network error'));

      await expect(
        useAuthStore.getState().oauthLogin('discord')
      ).rejects.toBeDefined();

      // Fallback pattern: `${provider} login failed`
      expect(useAuthStore.getState().error).toBe('discord login failed');
    });
  });

  // =========================================================================
  // oauthCallback
  // =========================================================================

  describe('oauthCallback', () => {
    it('test_oauthCallback_validates_CSRF_state_from_sessionStorage', async () => {
      sessionStorage.setItem('oauth_state', 'correct_state');

      // State mismatch should throw
      await expect(
        useAuthStore.getState().oauthCallback('google', 'code123', 'wrong_state')
      ).rejects.toThrow('OAuth state mismatch');
    });

    it('test_oauthCallback_handles_2FA_response', async () => {
      sessionStorage.setItem('oauth_state', 'valid_state');

      mockOauthLoginCallback.mockResolvedValue({
        data: {
          requires_2fa: true,
          tfa_token: 'tfa_abc',
          access_token: '',
          refresh_token: '',
          user: {
            id: 'u1',
            login: 'user1',
            email: 'test@test.com',
            is_active: true,
            is_email_verified: true,
            created_at: '2024-01-01',
          },
          is_new_user: false,
        },
      });

      const result = await useAuthStore.getState().oauthCallback('google', 'code123', 'valid_state');

      expect(result.requires_2fa).toBe(true);
      expect(result.tfa_token).toBe('tfa_abc');

      // Should NOT store tokens when 2FA is required
      expect(mockSetTokens).not.toHaveBeenCalled();

      // Should NOT be authenticated yet
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(useAuthStore.getState().isLoading).toBe(false);
    });

    it('test_oauthCallback_stores_tokens_on_success_without_2FA', async () => {
      sessionStorage.setItem('oauth_state', 'matched_state');

      mockOauthLoginCallback.mockResolvedValue({
        data: {
          requires_2fa: false,
          tfa_token: null,
          access_token: 'access_tok_123',
          refresh_token: 'refresh_tok_456',
          token_type: 'bearer',
          expires_in: 3600,
          user: {
            id: 'u2',
            login: 'testuser',
            email: 'u@example.com',
            is_active: true,
            is_email_verified: true,
            created_at: '2024-06-15',
          },
          is_new_user: false,
        },
      });

      const result = await useAuthStore.getState().oauthCallback('github', 'valid_code', 'matched_state');

      // Tokens should be stored
      expect(mockSetTokens).toHaveBeenCalledWith('access_tok_123', 'refresh_tok_456');

      // User should be set and authenticated
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user).toBeTruthy();
      expect(state.user?.id).toBe('u2');
      expect(state.user?.email).toBe('u@example.com');
      expect(state.isLoading).toBe(false);

      // Result should be the full response
      expect(result.requires_2fa).toBe(false);
    });

    it('test_oauthCallback_cleans_up_sessionStorage_on_success', async () => {
      sessionStorage.setItem('oauth_state', 'cleanup_state');
      sessionStorage.setItem('oauth_provider', 'apple');

      mockOauthLoginCallback.mockResolvedValue({
        data: {
          requires_2fa: false,
          access_token: 'tok',
          refresh_token: 'ref',
          user: {
            id: 'u3',
            login: 'user3',
            email: 'a@b.com',
            is_active: true,
            is_email_verified: true,
            created_at: '2024-01-01',
          },
          is_new_user: false,
        },
      });

      await useAuthStore.getState().oauthCallback('apple', 'code', 'cleanup_state');

      expect(sessionStorage.removeItem).toHaveBeenCalledWith('oauth_state');
      expect(sessionStorage.removeItem).toHaveBeenCalledWith('oauth_provider');
    });

    it('test_oauthCallback_cleans_up_sessionStorage_on_error', async () => {
      sessionStorage.setItem('oauth_state', 'err_state');
      sessionStorage.setItem('oauth_provider', 'microsoft');

      mockOauthLoginCallback.mockRejectedValue({
        response: { data: { detail: 'Invalid code' } },
      });

      await expect(
        useAuthStore.getState().oauthCallback('microsoft', 'bad', 'err_state')
      ).rejects.toBeDefined();

      expect(sessionStorage.removeItem).toHaveBeenCalledWith('oauth_state');
      expect(sessionStorage.removeItem).toHaveBeenCalledWith('oauth_provider');
    });

    it('test_oauthCallback_sets_error_on_failure', async () => {
      sessionStorage.setItem('oauth_state', 'fail_state');

      mockOauthLoginCallback.mockRejectedValue({
        response: { data: { detail: 'Invalid authorization code' } },
      });

      await expect(
        useAuthStore.getState().oauthCallback('google', 'bad_code', 'fail_state')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Invalid authorization code');
      expect(useAuthStore.getState().isLoading).toBe(false);
    });

    it('test_oauthCallback_uses_fallback_error_message', async () => {
      sessionStorage.setItem('oauth_state', 'st');

      mockOauthLoginCallback.mockRejectedValue(new Error('Network'));

      await expect(
        useAuthStore.getState().oauthCallback('github', 'code', 'st')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('OAuth callback failed');
    });
  });

  // =========================================================================
  // requestMagicLink
  // =========================================================================

  describe('requestMagicLink', () => {
    it('test_requestMagicLink_calls_api_with_email', async () => {
      mockRequestMagicLink.mockResolvedValue({ data: { message: 'Sent' } });

      await useAuthStore.getState().requestMagicLink('user@example.com');

      expect(mockRequestMagicLink).toHaveBeenCalledWith({ email: 'user@example.com' });
    });

    it('test_requestMagicLink_sets_loading_during_request', async () => {
      let resolvePromise: (value: unknown) => void;
      const deferredPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      mockRequestMagicLink.mockReturnValue(deferredPromise);

      const promise = useAuthStore.getState().requestMagicLink('test@test.com');

      expect(useAuthStore.getState().isLoading).toBe(true);

      resolvePromise!({ data: { message: 'OK' } });
      await promise;

      expect(useAuthStore.getState().isLoading).toBe(false);
    });

    it('test_requestMagicLink_sets_error_on_failure', async () => {
      mockRequestMagicLink.mockRejectedValue({
        response: { data: { detail: 'User not found' } },
      });

      await expect(
        useAuthStore.getState().requestMagicLink('nobody@example.com')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('User not found');
      expect(useAuthStore.getState().isLoading).toBe(false);
    });

    it('test_requestMagicLink_uses_fallback_error', async () => {
      mockRequestMagicLink.mockRejectedValue(new Error('Network'));

      await expect(
        useAuthStore.getState().requestMagicLink('e@e.com')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Failed to send magic link');
    });

    it('test_requestMagicLink_rate_limit_sets_rateLimitUntil', async () => {
      const rateLimitErr = new MockRateLimitError(120);
      mockRequestMagicLink.mockRejectedValue(rateLimitErr);

      await expect(
        useAuthStore.getState().requestMagicLink('e@e.com')
      ).rejects.toBeDefined();

      const state = useAuthStore.getState();
      expect(state.rateLimitUntil).toBeTruthy();
      expect(state.rateLimitUntil).toBeGreaterThan(Date.now());
    });
  });

  // =========================================================================
  // verifyMagicLink
  // =========================================================================

  describe('verifyMagicLink', () => {
    it('test_verifyMagicLink_stores_tokens_on_success', async () => {
      mockVerifyMagicLink.mockResolvedValue({
        data: {
          access_token: 'ml_access_tok',
          refresh_token: 'ml_refresh_tok',
          token_type: 'bearer',
          expires_in: 3600,
        },
      });

      mockMe.mockResolvedValue({
        data: {
          id: 'u4',
          email: 'magic@example.com',
          login: 'magicuser',
          role: 'user',
          is_active: true,
          is_email_verified: true,
          created_at: '2024-01-01',
        },
      });

      await useAuthStore.getState().verifyMagicLink('valid_magic_token');

      // Tokens should be stored
      expect(mockSetTokens).toHaveBeenCalledWith('ml_access_tok', 'ml_refresh_tok');

      // API should fetch user info
      expect(mockMe).toHaveBeenCalled();

      // User should be set and authenticated
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user?.id).toBe('u4');
      expect(state.user?.email).toBe('magic@example.com');
      expect(state.isLoading).toBe(false);
    });

    it('test_verifyMagicLink_calls_login_analytics_with_magic_link_method', async () => {
      mockVerifyMagicLink.mockResolvedValue({
        data: createMockTokenResponse(),
      });
      const mockUser = createMockUser({ id: 'ml_analytics_user' });
      mockMe.mockResolvedValue({ data: mockUser });

      await useAuthStore.getState().verifyMagicLink('tok');

      expect(mockLoginSuccess).toHaveBeenCalledWith('ml_analytics_user', 'magic_link');
    });

    it('test_verifyMagicLink_sets_error_on_failure', async () => {
      mockVerifyMagicLink.mockRejectedValue({
        response: { data: { detail: 'Token expired or invalid' } },
      });

      await expect(
        useAuthStore.getState().verifyMagicLink('expired_token')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Token expired or invalid');
      expect(useAuthStore.getState().isLoading).toBe(false);
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    it('test_verifyMagicLink_uses_fallback_error_message', async () => {
      mockVerifyMagicLink.mockRejectedValue(new Error('Network error'));

      await expect(
        useAuthStore.getState().verifyMagicLink('any_token')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Magic link verification failed');
    });
  });

  // =========================================================================
  // clearError and clearRateLimit
  // =========================================================================

  describe('clearError', () => {
    it('test_clearError_sets_error_to_null', () => {
      useAuthStore.setState({ error: 'some error' });
      expect(useAuthStore.getState().error).toBe('some error');

      useAuthStore.getState().clearError();
      expect(useAuthStore.getState().error).toBe(null);
    });

    it('test_clearError_is_idempotent_when_error_already_null', () => {
      useAuthStore.setState({ error: null });
      useAuthStore.getState().clearError();
      expect(useAuthStore.getState().error).toBe(null);
    });

    it('test_error_is_cleared_when_starting_new_action', async () => {
      useAuthStore.setState({ error: 'previous error' });

      mockRequestMagicLink.mockResolvedValue({ data: { message: 'OK' } });

      await useAuthStore.getState().requestMagicLink('fresh@example.com');

      expect(useAuthStore.getState().error).toBe(null);
    });
  });

  describe('clearRateLimit', () => {
    it('test_clearRateLimit_sets_rateLimitUntil_to_null', () => {
      useAuthStore.setState({ rateLimitUntil: Date.now() + 30000 });
      expect(useAuthStore.getState().rateLimitUntil).toBeTruthy();

      useAuthStore.getState().clearRateLimit();
      expect(useAuthStore.getState().rateLimitUntil).toBe(null);
    });

    it('test_clearRateLimit_is_idempotent_when_already_null', () => {
      useAuthStore.setState({ rateLimitUntil: null });
      useAuthStore.getState().clearRateLimit();
      expect(useAuthStore.getState().rateLimitUntil).toBe(null);
    });
  });

  // =========================================================================
  // Edge cases
  // =========================================================================

  describe('edge cases', () => {
    it('test_login_with_empty_email_passes_to_api', async () => {
      // Arrange - empty values should still be passed through; validation is server-side
      mockLogin.mockRejectedValue({
        response: { data: { detail: 'Email is required' } },
      });

      // Act & Assert
      await expect(
        useAuthStore.getState().login('', '')
      ).rejects.toBeDefined();

      expect(mockLogin).toHaveBeenCalledWith({
        email: '',
        password: '',
        remember_me: false,
      });
      expect(useAuthStore.getState().error).toBe('Email is required');
    });

    it('test_register_with_email_having_no_at_symbol', async () => {
      // The store derives login from email.split('@')[0]
      // With no '@', the full email becomes the login
      mockRegister.mockResolvedValue({
        data: {
          id: 'usr_edge',
          login: 'noatsymbol',
          email: 'noatsymbol',
          is_active: false,
          is_email_verified: false,
        },
      });

      await useAuthStore.getState().register('noatsymbol', 'password');

      expect(mockRegister).toHaveBeenCalledWith({
        login: 'noatsymbol',
        email: 'noatsymbol',
        password: 'password',
      });
    });

    it('test_multiple_sequential_actions_maintain_consistent_state', async () => {
      // login -> logout -> fetchUser should leave a clean state
      // Step 1: Login
      mockLogin.mockResolvedValue({ data: createMockTokenResponse() });
      mockMe.mockResolvedValue({ data: createMockUser() });
      await useAuthStore.getState().login('e@e.com', 'p');
      expect(useAuthStore.getState().isAuthenticated).toBe(true);

      // Step 2: Logout
      mockLogout.mockResolvedValue({ data: {} });
      await useAuthStore.getState().logout();
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(useAuthStore.getState().user).toBe(null);

      // Step 3: fetchUser fails (no token)
      mockMe.mockRejectedValue(new Error('Unauthorized'));
      await useAuthStore.getState().fetchUser();
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(useAuthStore.getState().user).toBe(null);
    });

    it('test_concurrent_error_and_loading_reset_properly', async () => {
      // Set error state, then start a new action that succeeds
      useAuthStore.setState({ error: 'old error', isLoading: false });

      mockLogin.mockResolvedValue({ data: createMockTokenResponse() });
      mockMe.mockResolvedValue({ data: createMockUser() });

      await useAuthStore.getState().login('e@e.com', 'p');

      const state = useAuthStore.getState();
      expect(state.error).toBe(null);
      expect(state.isLoading).toBe(false);
      expect(state.isAuthenticated).toBe(true);
    });
  });
});
