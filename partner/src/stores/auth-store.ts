import { create } from 'zustand';
import { authApi, type User } from '@/lib/api/auth';
import { RateLimitError, tokenStorage } from '@/lib/api/client';
import { authAnalytics } from '@/lib/analytics';
import { defaultLocale } from '@/i18n/config';
import { stagePendingTwoFactorSession } from '@/features/auth/lib/pending-twofa-client';
import { getDefaultPostLoginPath, getSafeRedirectPath } from '@/features/auth/lib/redirect-path';
import {
  buildLocalizedAccessDeniedLoginPath,
  hasPartnerPortalAccess,
} from '@/features/auth/lib/partner-access';

let fetchUserInFlight: Promise<void> | null = null;

function getActiveLocale(): string {
  if (typeof window === 'undefined') {
    return defaultLocale;
  }

  const match = window.location.pathname.match(/^\/([a-z]{2,3}-[A-Z]{2})(?:\/|$)/);
  return match ? match[1] : defaultLocale;
}

function getPostLoginRedirect(locale: string): string {
  if (typeof window === 'undefined') {
    return getDefaultPostLoginPath(locale);
  }

  const searchParams = new URLSearchParams(window.location.search);
  return getSafeRedirectPath(searchParams.get('redirect'), locale);
}

function buildTwoFactorLoginUrl(locale: string, redirectTarget: string): string {
  const params = new URLSearchParams({ '2fa': 'true' });
  if (redirectTarget) {
    params.set('redirect', redirectTarget);
  }
  return `/${locale}/login?${params.toString()}`;
}

async function clearUnauthorizedAdminSession(): Promise<void> {
  try {
    await authApi.logout();
  } catch {
    // Best effort cleanup; cookies may already be invalid or partially issued.
  } finally {
    tokenStorage.clearTokens();
  }
}

function readErrorMessage(error: unknown, fallback: string): string {
  const axiosError = error as { response?: { status?: number; data?: { detail?: unknown } } };
  const detail = axiosError.response?.data?.detail;

  if (axiosError.response?.status === 423) {
    return 'Account temporarily locked. Please try again later.';
  }
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((err: { msg?: string }) => err.msg || JSON.stringify(err)).join(', ');
  }
  if (typeof detail === 'object' && detail !== null) {
    return JSON.stringify(detail);
  }

  return fallback;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isNewTelegramUser: boolean;
  isMiniApp: boolean;
  error: string | null;
  rateLimitUntil: number | null;
  login: (email: string, password: string) => Promise<void>;
  register: (
    identifier: string,
    password: string,
    options?: {
      mode?: 'email' | 'username';
      tos_accepted?: boolean;
      marketing_consent?: boolean;
    },
  ) => Promise<void>;
  verifyOtpAndLogin: (email: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
  clearError: () => void;
  clearRateLimit: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  isLoading: false,
  isAuthenticated: false,
  isNewTelegramUser: false,
  isMiniApp: false,
  error: null,
  rateLimitUntil: null,

  login: async (email, password) => {
    authAnalytics.loginStarted();
    set({ isLoading: true, error: null, rateLimitUntil: null });

    try {
      const { data } = await authApi.login({ email, password });

      if (data.requires_2fa && data.tfa_token) {
        const locale = getActiveLocale();
        const redirectTarget = getPostLoginRedirect(locale);

        await stagePendingTwoFactorSession({
          token: data.tfa_token,
          locale,
          returnTo: redirectTarget,
        });

        set({ isLoading: false, isAuthenticated: false, error: null });
        if (typeof window !== 'undefined') {
          window.location.href = buildTwoFactorLoginUrl(locale, redirectTarget);
        }
        return;
      }

      const { data: user } = await authApi.session();
      if (!hasPartnerPortalAccess(user)) {
        const locale = getActiveLocale();
        await clearUnauthorizedAdminSession();
        set({ user: null, isAuthenticated: false, isLoading: false, error: null });
        if (typeof window !== 'undefined') {
          window.location.href = buildLocalizedAccessDeniedLoginPath(locale);
        }
        return;
      }

      set({ user, isAuthenticated: true, isLoading: false, error: null });
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

      const message = readErrorMessage(error, 'Login failed');
      authAnalytics.loginError(message);
      set({ error: message, isLoading: false, isAuthenticated: false, user: null });
      throw error;
    }
  },

  register: async (identifier, password, options) => {
    authAnalytics.registerStarted();
    set({ isLoading: true, error: null, rateLimitUntil: null });

    try {
      const mode = options?.mode ?? 'email';
      const trimmedIdentifier = identifier.trim();
      const payload = mode === 'username'
        ? {
            login: trimmedIdentifier,
            password,
            tos_accepted: options?.tos_accepted ?? true,
            marketing_consent: options?.marketing_consent ?? false,
          }
        : {
            login: trimmedIdentifier.split('@')[0] || trimmedIdentifier,
            email: trimmedIdentifier,
            password,
            tos_accepted: options?.tos_accepted ?? true,
            marketing_consent: options?.marketing_consent ?? false,
          };

      const { data } = await authApi.register(payload);

      set({
        user: {
          id: data.id,
          email: data.email ?? null,
          login: data.login,
          role: 'user',
          is_active: data.is_active,
          is_email_verified: data.is_email_verified,
          created_at: new Date().toISOString(),
        },
        isAuthenticated: false,
        isLoading: false,
        error: null,
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

      const message = readErrorMessage(error, 'Registration failed');
      authAnalytics.registerError(message);
      set({ error: message, isLoading: false, isAuthenticated: false });
      throw error;
    }
  },

  verifyOtpAndLogin: async (email, code) => {
    set({ isLoading: true, error: null, rateLimitUntil: null });

    try {
      await authApi.verifyOtp({ email, code });
      const { data: user } = await authApi.session();

      if (!hasPartnerPortalAccess(user)) {
        const locale = getActiveLocale();
        await clearUnauthorizedAdminSession();
        set({ user: null, isAuthenticated: false, isLoading: false, error: null });
        if (typeof window !== 'undefined') {
          window.location.href = buildLocalizedAccessDeniedLoginPath(locale);
        }
        return;
      }

      set({
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
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

      const message = readErrorMessage(error, 'Verification failed');
      set({ error: message, isLoading: false, isAuthenticated: false });
      throw error;
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      await authApi.logout();
    } finally {
      tokenStorage.clearTokens();
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        isNewTelegramUser: false,
      });
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
        if (!hasPartnerPortalAccess(data)) {
          const locale = getActiveLocale();
          await clearUnauthorizedAdminSession();
          set({ user: null, isAuthenticated: false, isLoading: false, error: null });
          if (typeof window !== 'undefined') {
            window.location.href = buildLocalizedAccessDeniedLoginPath(locale);
          }
          return;
        }
        set({ user: data, isAuthenticated: true, isLoading: false, error: null });
        authAnalytics.sessionRestored(data.id);
      } catch {
        set({ user: null, isAuthenticated: false, isLoading: false });
      } finally {
        fetchUserInFlight = null;
      }
    })();

    await fetchUserInFlight;
  },

  clearError: () => set({ error: null }),
  clearRateLimit: () => set({ rateLimitUntil: null }),
}));

export const useUser = () => useAuthStore((s) => s.user);
export const useIsAuthenticated = () => useAuthStore((s) => s.isAuthenticated);
export const useAuthLoading = () => useAuthStore((s) => s.isLoading);
export const useAuthError = () => useAuthStore((s) => s.error);
export const useRateLimitUntil = () => useAuthStore((s) => s.rateLimitUntil);
export const useIsNewTelegramUser = () => useAuthStore((s) => s.isNewTelegramUser);
export const useIsMiniApp = () => useAuthStore((s) => s.isMiniApp);
