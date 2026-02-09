import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Use vi.hoisted() so these mock functions are available when vi.mock factories run
const {
  mockOauthLoginAuthorize,
  mockOauthLoginCallback,
  mockRequestMagicLink,
  mockVerifyMagicLink,
  mockMe,
  mockSetTokens,
  mockClearTokens,
} = vi.hoisted(() => ({
  mockOauthLoginAuthorize: vi.fn(),
  mockOauthLoginCallback: vi.fn(),
  mockRequestMagicLink: vi.fn(),
  mockVerifyMagicLink: vi.fn(),
  mockMe: vi.fn(),
  mockSetTokens: vi.fn(),
  mockClearTokens: vi.fn(),
}));

// Mock authApi
vi.mock('@/lib/api/auth', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    verifyOtp: vi.fn(),
    logout: vi.fn(),
    me: mockMe,
    telegramWidget: vi.fn(),
    telegramMiniApp: vi.fn(),
    oauthLoginAuthorize: mockOauthLoginAuthorize,
    oauthLoginCallback: mockOauthLoginCallback,
    requestMagicLink: mockRequestMagicLink,
    verifyMagicLink: mockVerifyMagicLink,
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
  RateLimitError: class RateLimitError extends Error {
    retryAfter: number;
    constructor(retryAfter: number) {
      super(`Rate limited. Try again in ${retryAfter} seconds`);
      this.name = 'RateLimitError';
      this.retryAfter = retryAfter;
    }
  },
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

// Import AFTER mocks are set up
import { useAuthStore } from '../auth-store';

describe('Auth Store - OAuth and Magic Link actions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store state between tests
    useAuthStore.setState({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      error: null,
      rateLimitUntil: null,
    });
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('oauthLogin', () => {
    it('stores provider in sessionStorage and redirects', async () => {
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

    it('sets loading state during oauth login', async () => {
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

    it('sets error on oauth login failure', async () => {
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
  });

  describe('oauthCallback', () => {
    it('validates CSRF state from sessionStorage', async () => {
      sessionStorage.setItem('oauth_state', 'correct_state');

      // State mismatch should throw
      await expect(
        useAuthStore.getState().oauthCallback('google', 'code123', 'wrong_state')
      ).rejects.toThrow('OAuth state mismatch');
    });

    it('handles 2FA response (requires_2fa=true)', async () => {
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

    it('stores tokens on successful callback (no 2FA)', async () => {
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

    it('cleans up sessionStorage after callback', async () => {
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

    it('cleans up sessionStorage on error too', async () => {
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
  });

  describe('requestMagicLink', () => {
    it('calls authApi.requestMagicLink with the email', async () => {
      mockRequestMagicLink.mockResolvedValue({ data: { message: 'Sent' } });

      await useAuthStore.getState().requestMagicLink('user@example.com');

      expect(mockRequestMagicLink).toHaveBeenCalledWith({ email: 'user@example.com' });
    });

    it('sets loading state during request', async () => {
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

    it('sets error state on failure', async () => {
      mockRequestMagicLink.mockRejectedValue({
        response: { data: { detail: 'User not found' } },
      });

      await expect(
        useAuthStore.getState().requestMagicLink('nobody@example.com')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('User not found');
      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });

  describe('verifyMagicLink', () => {
    it('stores tokens on successful verification', async () => {
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

    it('sets error on verification failure', async () => {
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

    it('uses fallback error message when detail is not available', async () => {
      mockVerifyMagicLink.mockRejectedValue(new Error('Network error'));

      await expect(
        useAuthStore.getState().verifyMagicLink('any_token')
      ).rejects.toBeDefined();

      expect(useAuthStore.getState().error).toBe('Magic link verification failed');
    });
  });

  describe('error handling', () => {
    it('clearError sets error to null', () => {
      useAuthStore.setState({ error: 'some error' });
      expect(useAuthStore.getState().error).toBe('some error');

      useAuthStore.getState().clearError();
      expect(useAuthStore.getState().error).toBe(null);
    });

    it('error is cleared when starting a new action', async () => {
      useAuthStore.setState({ error: 'previous error' });

      mockRequestMagicLink.mockResolvedValue({ data: { message: 'OK' } });

      await useAuthStore.getState().requestMagicLink('fresh@example.com');

      expect(useAuthStore.getState().error).toBe(null);
    });
  });
});
