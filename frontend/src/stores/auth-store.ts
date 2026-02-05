import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { authApi, User, TelegramWidgetData } from '@/lib/api/auth';
import { RateLimitError } from '@/lib/api/client';
import { authAnalytics } from '@/lib/analytics';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  rateLimitUntil: number | null; // Timestamp when rate limit expires

  // Actions
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
  telegramAuth: (data: TelegramWidgetData) => Promise<void>;
  telegramMiniAppAuth: () => Promise<void>;
  clearError: () => void;
  clearRateLimit: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      error: null,
      rateLimitUntil: null,

      login: async (email, password, rememberMe = false) => {
        authAnalytics.loginStarted();
        set({ isLoading: true, error: null, rateLimitUntil: null });
        try {
          // Login returns tokens, then fetch user info
          await authApi.login({ email, password, remember_me: rememberMe });
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
              role: 'user',
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

      logout: async () => {
        set({ isLoading: true });
        try {
          await authApi.logout();
        } finally {
          set({ user: null, isAuthenticated: false, isLoading: false, error: null });
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
        set({ isLoading: true, error: null });
        try {
          const { data } = await authApi.telegramWidget(widgetData);
          set({ user: data.user, isAuthenticated: true, isLoading: false });
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
        try {
          const initData = window.Telegram.WebApp.initData;
          const { data } = await authApi.telegramMiniApp(initData);
          set({ user: data.user, isAuthenticated: true, isLoading: false });
          authAnalytics.telegramSuccess(data.user.id);
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Telegram Mini App auth failed';
          authAnalytics.telegramError(message);
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
