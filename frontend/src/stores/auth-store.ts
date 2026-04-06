import { create } from 'zustand';
import {
  authApi,
  type AuthResponse,
  type BotLinkResponse,
  type OAuthProvider,
  type TelegramMiniAppResponse,
  type TelegramWidgetData,
  type User,
} from '@/lib/api/auth';
import { RateLimitError, tokenStorage } from '@/lib/api/client';
import { authAnalytics } from '@/lib/analytics';
import {
  clearTelegramMagicLinkSession,
  saveTelegramMagicLinkSession,
} from '@/features/auth/lib/telegram-magic-link-session';
import { getDefaultPostLoginPath, getSafeRedirectPath } from '@/features/auth/lib/redirect-path';

let fetchUserInFlight: Promise<void> | null = null;

function getLocalePrefix(): string {
  if (typeof window === 'undefined') return '/en-EN';

  const match = window.location.pathname.match(/^\/([a-z]{2,3}-[A-Z]{2})(?:\/|$)/);
  return match ? `/${match[1]}` : '/en-EN';
}

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
  register: (
    identifier: string,
    password: string,
    options?: { mode?: 'email' | 'username' }
  ) => Promise<void>;
  verifyOtpAndLogin: (email: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
  telegramAuth: (data: TelegramWidgetData) => Promise<AuthResponse>;
  telegramMiniAppAuth: () => Promise<TelegramMiniAppResponse>;
  telegramMagicLinkAuth: () => Promise<void>;
  loginWithBotLink: (token: string) => Promise<BotLinkResponse>;
  oauthLogin: (provider: OAuthProvider) => Promise<void>;
  requestMagicLink: (email: string) => Promise<void>;
  verifyMagicLink: (token: string) => Promise<void>;
  verifyMagicLinkOtp: (email: string, code: string) => Promise<void>;
  deleteAccount: () => Promise<void>;
  clearError: () => void;
  clearRateLimit: () => void;
}

export const useAuthStore = create<AuthState>()(
    (set, get) => ({
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
          const { data: user } = await authApi.session();
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
          const axiosError = error as { response?: { data?: { detail?: unknown } } };
          const detail = axiosError.response?.data?.detail;
          let message = 'Login failed';

          if (typeof detail === 'string') {
            message = detail;
          } else if (Array.isArray(detail)) {
            message = detail.map((err: { msg?: string }) => err.msg || JSON.stringify(err)).join(', ');
          } else if (typeof detail === 'object' && detail !== null) {
            message = JSON.stringify(detail);
          }

          authAnalytics.loginError(message);
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      register: async (identifier, password, options) => {
        authAnalytics.registerStarted();
        set({ isLoading: true, error: null, rateLimitUntil: null });
        try {
          const mode = options?.mode ?? 'email';
          const payload = mode === 'username'
            ? { login: identifier.trim(), password }
            : { login: identifier.split('@')[0], email: identifier.trim(), password };
          const { data } = await authApi.register(payload);
          // User is registered but NOT authenticated yet - needs OTP verification
          // Store minimal user info for OTP flow, but don't set isAuthenticated
          set({
            user: {
              id: data.id,
              email: data.email ?? '',
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

          const axiosError = error as { response?: { data?: { detail?: unknown } } };
          const detail = axiosError.response?.data?.detail;
          let message = 'Registration failed';

          if (typeof detail === 'string') {
            message = detail;
          } else if (Array.isArray(detail)) {
            // Handle Pydantic validation errors (array of objects)
            message = detail.map((err: { msg?: string }) => err.msg || JSON.stringify(err)).join(', ');
          } else if (typeof detail === 'object' && detail !== null) {
            message = JSON.stringify(detail);
          }

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
          const detail = axiosError.response?.data?.detail;
          let message = 'Verification failed';

          if (typeof detail === 'string') {
            message = detail;
          } else if (Array.isArray(detail)) {
            message = detail.map((err: { msg?: string }) => err.msg || JSON.stringify(err)).join(', ');
          } else if (typeof detail === 'object' && detail !== null) {
            if ('detail' in detail) {
              message = (detail as { detail: string }).detail;
            } else {
              message = JSON.stringify(detail);
            }
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
        if (fetchUserInFlight) {
          await fetchUserInFlight;
          return;
        }

        fetchUserInFlight = (async () => {
          try {
            const { data } = await authApi.session();
            set({ user: data, isAuthenticated: true, isLoading: false });
            authAnalytics.sessionRestored(data.id);
          } catch {
            set({ user: null, isAuthenticated: false, isLoading: false });
          } finally {
            fetchUserInFlight = null;
          }
        })();

        await fetchUserInFlight;
      },

      telegramAuth: async (widgetData) => {
        authAnalytics.telegramStarted();
        set({ isLoading: true, error: null, isNewTelegramUser: false });
        try {
          // 2026 approach using secure web endpoint
          const { data } = await authApi.telegramWebLogin(widgetData);
          if (data.requires_2fa) {
            set({ isLoading: false, isAuthenticated: false });
            return data;
          }

          const isNewUser = data.is_new_user ?? false;
          set({ user: data.user, isAuthenticated: true, isLoading: false, isNewTelegramUser: isNewUser });
          authAnalytics.telegramSuccess(data.user.id);
          return data;
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
            if (data.requires_2fa) {
              set({ isLoading: false, isAuthenticated: false });
              return data;
            }

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
            return data;
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

      telegramMagicLinkAuth: async () => {
        authAnalytics.telegramStarted();
        set({ isLoading: true, error: null });
        try {
          clearTelegramMagicLinkSession();
          const { data } = await authApi.requestTelegramMagicLink();

          saveTelegramMagicLinkSession({
            token: data.token,
            botUrl: data.bot_url,
            deepLinkUrl: data.deep_link_url,
            requestedAt: Date.now(),
          });

          window.open(data.deep_link_url ?? data.bot_url, '_blank', 'noopener,noreferrer');

          set({ isLoading: false });
          window.location.href = `${getLocalePrefix()}/telegram-link?magic=${encodeURIComponent(data.token)}`;
        } catch (error: unknown) {
          clearTelegramMagicLinkSession();
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Failed to start Magic Link auth';
          authAnalytics.telegramError(message);
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      loginWithBotLink: async (token) => {
        set({ isLoading: true, error: null });
        try {
          // SEC-01: backend sets httpOnly cookies
          const { data } = await authApi.telegramBotLink({ token });
          if (data.requires_2fa) {
            set({ isLoading: false, isAuthenticated: false });
            return data;
          }

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
          return data;
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Bot link login failed';
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      oauthLogin: async (provider) => {
        if (provider === 'telegram') {
          return get().telegramMagicLinkAuth();
        }

        authAnalytics.oauthStarted(provider);
        set({ isLoading: true, error: null });
        try {
          const locale = getLocalePrefix().slice(1);
          const searchParams = new URLSearchParams(window.location.search);
          const returnTo = getSafeRedirectPath(
            searchParams.get('redirect'),
            locale,
          ) || getDefaultPostLoginPath(locale);
          const startUrl = new URL(`/api/oauth/start/${provider}`, window.location.origin);
          startUrl.searchParams.set('locale', locale);
          startUrl.searchParams.set('return_to', returnTo);
          window.location.href = startUrl.toString();
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || `${provider} login failed`;
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
          // Backend returns user data directly — no separate /auth/me call needed
          const { data } = await authApi.verifyMagicLink({ token });
          set({
            user: {
              id: data.user.id,
              email: data.user.email || '',
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
          authAnalytics.loginSuccess(data.user.id, 'magic_link');
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Magic link verification failed';
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      verifyMagicLinkOtp: async (email, code) => {
        set({ isLoading: true, error: null });
        try {
          // Backend returns user data directly — no separate /auth/me call needed
          const { data } = await authApi.verifyMagicLinkOtp({ email, code });
          set({
            user: {
              id: data.user.id,
              email: data.user.email || '',
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
          authAnalytics.loginSuccess(data.user.id, 'magic_link_otp');
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Code verification failed';
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
    })
);

// Selector hooks for optimized re-renders
export const useUser = () => useAuthStore((s) => s.user);
export const useIsAuthenticated = () => useAuthStore((s) => s.isAuthenticated);
export const useAuthLoading = () => useAuthStore((s) => s.isLoading);
export const useAuthError = () => useAuthStore((s) => s.error);
export const useRateLimitUntil = () => useAuthStore((s) => s.rateLimitUntil);
export const useIsNewTelegramUser = () => useAuthStore((s) => s.isNewTelegramUser);
export const useIsMiniApp = () => useAuthStore((s) => s.isMiniApp);
