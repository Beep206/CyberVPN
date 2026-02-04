import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { authApi, User, TelegramWidgetData } from '@/lib/api/auth';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
  telegramAuth: (data: TelegramWidgetData) => Promise<void>;
  telegramMiniAppAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      error: null,

      login: async (email, password, rememberMe = false) => {
        set({ isLoading: true, error: null });
        try {
          const { data } = await authApi.login({ email, password, remember_me: rememberMe });
          set({ user: data.user, isAuthenticated: true, isLoading: false });
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Login failed';
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      register: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const { data } = await authApi.register({ email, password });
          set({ user: data.user, isAuthenticated: true, isLoading: false });
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Registration failed';
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
        }
      },

      fetchUser: async () => {
        set({ isLoading: true });
        try {
          const { data } = await authApi.me();
          set({ user: data, isAuthenticated: true, isLoading: false });
        } catch {
          set({ user: null, isAuthenticated: false, isLoading: false });
        }
      },

      telegramAuth: async (widgetData) => {
        set({ isLoading: true, error: null });
        try {
          const { data } = await authApi.telegramWidget(widgetData);
          set({ user: data.user, isAuthenticated: true, isLoading: false });
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Telegram auth failed';
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      telegramMiniAppAuth: async () => {
        if (typeof window === 'undefined' || !window.Telegram?.WebApp) {
          throw new Error('Not in Telegram Mini App context');
        }

        set({ isLoading: true, error: null });
        try {
          const initData = window.Telegram.WebApp.initData;
          const { data } = await authApi.telegramMiniApp(initData);
          set({ user: data.user, isAuthenticated: true, isLoading: false });
        } catch (error: unknown) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const message = axiosError.response?.data?.detail || 'Telegram Mini App auth failed';
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      clearError: () => set({ error: null }),
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
