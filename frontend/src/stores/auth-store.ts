import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { authApi, type User, type TelegramWidgetData, type OAuthProvider, type OAuthLoginResponse } from '@/lib/api/auth';
import { RateLimitError, tokenStorage } from '@/lib/api/client';
import { authAnalytics } from '@/lib/analytics';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isNewTelegramUser: boolean;
  isMiniApp: boolean;
  error: string | null;
  rateLimitUntil: number | null; // Timestamp when rate limit expires

  // Actions
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  verifyOtpAndLogin: (email: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
  telegramAuth: (data: TelegramWidgetData) => Promise<void>;
  telegramMiniAppAuth: () => Promise<void>;
  loginWithBotLink: (token: string) => Promise<void>;
  oauthLogin: (provider: OAuthProvider) => Promise<void>;
  oauthCallback: (provider: OAuthProvider, code: string, state: string) => Promise<OAuthLoginResponse>;
  requestMagicLink: (email: string) => Promise<void>;
  verifyMagicLink: (token: string) => Promise<void>;
  deleteAccount: () => Promise<void>;
  clearError: () => void;
  clearRateLimit: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      isNewTelegramUser: false,
      isMiniApp: typeof window !== 'undefined' && !!window.Telegram?.WebApp?.initData,
      error: null,
      rateLimitUntil: null,

      login: async (email, password, rememberMe = false) => {
        authAnalytics.loginStarted();
        set({ isLoading: true, error: null, rateLimitUntil: null });
        try {
          // SEC-01: backend sets httpOnly cookies automatically
          await authApi.login({ email, password, remember_me: rememberMe });

          // Fetch user info (auth via httpOnly cookie)
          const { data: user } = await authApi.me();
          set({ user, isAuthenticated: true, isLoading: false });
          authAnalytics.loginSuccess(user.id, 'email');
        } catch (error: unknown) {
          if (error instanceof RateLimitError) {
            authAnalytics.rateLimited(error.retryAfter);
            set({
              error: error.message,
              isLoading: false,
              rateLimitUntil: Date.now() + error.retryAfter * 1000,
            });
            throw error;
          }
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Login failed';
          authAnalytics.loginError(message);
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      register: async (email, password) => {
        authAnalytics.registerStarted();
        set({ isLoading: true, error: null, rateLimitUntil: null });
        try {
          // Generate login from email (part before @)
          const login = email.split('@')[0];
          const { data } = await authApi.register({ login, email, password });
          // User is registered but NOT authenticated yet - needs OTP verification
          // Store minimal user info for OTP flow, but don't set isAuthenticated
          set({
            user: {
              id: data.id,
              email: data.email,
              login: data.login,
              is_active: data.is_active,
              is_email_verified: data.is_email_verified,
              role: 'viewer',  // Default role for new users
              created_at: new Date().toISOString(),
            },
            isAuthenticated: false,
            isLoading: false
          });
          authAnalytics.registerSuccess(data.id);
        } catch (error: unknown) {
          if (error instanceof RateLimitError) {
            authAnalytics.rateLimited(error.retryAfter);
            set({
              error: error.message,
              isLoading: false,
              rateLimitUntil: Date.now() + error.retryAfter * 1000,
            });
            throw error;
          }
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Registration failed';
          authAnalytics.registerError(message);
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      verifyOtpAndLogin: async (email, code) => {
        set({ isLoading: true, error: null });
        try {
          // SEC-01: backend sets httpOnly cookies; we just need user data
          const { data } = await authApi.verifyOtp({ email, code });

          // User is now verified and authenticated
          set({
            user: {
              id: data.user.id,
              email: data.user.email,
              login: data.user.login,
              is_active: data.user.is_active,
              is_email_verified: data.user.is_email_verified,
              role: data.user.role,
              created_at: data.user.created_at,
              telegram_id: data.user.telegram_id,
            },
            isAuthenticated: true,
            isLoading: false,
          });
          authAnalytics.loginSuccess(data.user.id, 'email');
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: unknown } } };
          const errorDetail = axiosError.response?.data?.detail;
          let message = 'Verification failed';

          if (typeof errorDetail === 'object' && errorDetail !== null && 'detail' in errorDetail) {
            message = (errorDetail as { detail: string }).detail;
          } else if (typeof errorDetail === 'string') {
            message = errorDetail;
          }

          set({ error: message, isLoading: false });
          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          await authApi.logout();
        } finally {
          // SEC-01: backend clears cookies; clean up any legacy localStorage
          tokenStorage.clearTokens();
          set({ user: null, isAuthenticated: false, isLoading: false, error: null, isNewTelegramUser: false });
          authAnalytics.logout();
        }
      },

      fetchUser: async () => {
        set({ isLoading: true });
        try {
          const { data } = await authApi.me();
          set({ user: data, isAuthenticated: true, isLoading: false });
          authAnalytics.sessionRestored(data.id);
        } catch {
          set({ user: null, isAuthenticated: false, isLoading: false });
        }
      },

      telegramAuth: async (widgetData) => {
        authAnalytics.telegramStarted();
        set({ isLoading: true, error: null, isNewTelegramUser: false });
        try {
          const { data } = await authApi.telegramWidget(widgetData);
          const isNewUser = data.is_new_user ?? false;
          set({ user: data.user, isAuthenticated: true, isLoading: false, isNewTelegramUser: isNewUser });
          authAnalytics.telegramSuccess(data.user.id);
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Telegram auth failed';
          authAnalytics.telegramError(message);
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      telegramMiniAppAuth: async () => {
        if (typeof window === 'undefined' || !window.Telegram?.WebApp) {
          throw new Error('Not in Telegram Mini App context');
        }

        authAnalytics.telegramStarted();
        set({ isLoading: true, error: null });

        const initData = window.Telegram.WebApp.initData;
        let lastError: unknown;

        // 1 retry on failure
        for (let attempt = 0; attempt < 2; attempt++) {
          try {
            // SEC-01: backend sets httpOnly cookies
            const { data } = await authApi.telegramMiniApp(initData);
            const isNewUser = data.is_new_user ?? false;
            set({
              user: {
                id: data.user.id,
                email: data.user.email || '',
                login: data.user.login,
                is_active: data.user.is_active,
                is_email_verified: data.user.is_email_verified,
                role: 'viewer',
                created_at: data.user.created_at,
              },
              isAuthenticated: true,
              isLoading: false,
              isNewTelegramUser: isNewUser,
            });
            authAnalytics.telegramSuccess(data.user.id);
            return;
          } catch (error: unknown) {
            lastError = error;
            if (attempt === 0) {
              // Wait briefly before retry
              await new Promise((r) => setTimeout(r, 500));
            }
          }
        }

        const axiosError = lastError as { response?: { data?: { detail?: string } } };
        const message = axiosError?.response?.data?.detail || 'Telegram Mini App auth failed';
        authAnalytics.telegramError(message);
        set({ error: message, isLoading: false });
        throw lastError;
      },

      loginWithBotLink: async (token) => {
        set({ isLoading: true, error: null });
        try {
          // SEC-01: backend sets httpOnly cookies
          const { data } = await authApi.telegramBotLink({ token });
          set({
            user: {
              id: data.user.id,
              email: data.user.email || '',
              login: data.user.login,
              is_active: data.user.is_active,
              is_email_verified: data.user.is_email_verified,
              role: 'viewer',
              created_at: data.user.created_at,
            },
            isAuthenticated: true,
            isLoading: false,
          });
          authAnalytics.loginSuccess(data.user.id, 'telegram');
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Bot link login failed';
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      oauthLogin: async (provider) => {
        set({ isLoading: true, error: null });
        try {
          const redirectUri = `${window.location.origin}/auth/callback/${provider}`;
          const { data } = await authApi.oauthLoginAuthorize(provider, redirectUri);
          // Store state in sessionStorage for CSRF validation on callback
          sessionStorage.setItem('oauth_state', data.state);
          sessionStorage.setItem('oauth_provider', provider);
          // Redirect to provider
          window.location.href = data.authorize_url;
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || `${provider} login failed`;
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      oauthCallback: async (provider, code, state) => {
        set({ isLoading: true, error: null });
        try {
          // Verify state matches stored value
          const storedState = sessionStorage.getItem('oauth_state');
          if (state !== storedState) {
            throw new Error('OAuth state mismatch - possible CSRF attack');
          }

          const redirectUri = `${window.location.origin}/auth/callback/${provider}`;
          const { data } = await authApi.oauthLoginCallback(provider, {
            code,
            state,
            redirect_uri: redirectUri,
          });

          // Clean up sessionStorage
          sessionStorage.removeItem('oauth_state');
          sessionStorage.removeItem('oauth_provider');

          // If 2FA required, return the response for the caller to handle
          if (data.requires_2fa) {
            set({ isLoading: false });
            return data;
          }

          // SEC-01: backend sets httpOnly cookies; set user state
          set({
            user: {
              id: data.user.id,
              email: data.user.email || '',
              login: data.user.login,
              is_active: data.user.is_active,
              is_email_verified: data.user.is_email_verified,
              role: 'viewer',
              created_at: data.user.created_at,
            },
            isAuthenticated: true,
            isLoading: false,
          });
          authAnalytics.loginSuccess(data.user.id, provider);
          return data;
        } catch (error: unknown) {
          sessionStorage.removeItem('oauth_state');
          sessionStorage.removeItem('oauth_provider');
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'OAuth callback failed';
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      requestMagicLink: async (email) => {
        set({ isLoading: true, error: null });
        try {
          await authApi.requestMagicLink({ email });
          set({ isLoading: false });
        } catch (error: unknown) {
          if (error instanceof RateLimitError) {
            set({
              error: error.message,
              isLoading: false,
              rateLimitUntil: Date.now() + error.retryAfter * 1000,
            });
            throw error;
          }
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Failed to send magic link';
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      verifyMagicLink: async (token) => {
        set({ isLoading: true, error: null });
        try {
          // SEC-01: backend sets httpOnly cookies
          await authApi.verifyMagicLink({ token });

          // Fetch full user info
          const { data: user } = await authApi.me();
          set({ user, isAuthenticated: true, isLoading: false });
          authAnalytics.loginSuccess(user.id, 'magic_link');
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Magic link verification failed';
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      deleteAccount: async () => {
        set({ isLoading: true, error: null });
        try {
          await authApi.deleteAccount();
          // SEC-01: backend clears cookies; clean up legacy localStorage
          tokenStorage.clearTokens();
          set({ user: null, isAuthenticated: false, isLoading: false, error: null, isNewTelegramUser: false });
          authAnalytics.logout();
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Account deletion failed';
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      clearError: () => set({ error: null }),
      clearRateLimit: () => set({ rateLimitUntil: null }),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);

// Selector hooks for optimized re-renders
export const useUser = () => useAuthStore((s) => s.user);
export const useIsAuthenticated = () => useAuthStore((s) => s.isAuthenticated);
export const useAuthLoading = () => useAuthStore((s) => s.isLoading);
export const useAuthError = () => useAuthStore((s) => s.error);
export const useRateLimitUntil = () => useAuthStore((s) => s.rateLimitUntil);
export const useIsNewTelegramUser = () => useAuthStore((s) => s.isNewTelegramUser);
export const useIsMiniApp = () => useAuthStore((s) => s.isMiniApp);
