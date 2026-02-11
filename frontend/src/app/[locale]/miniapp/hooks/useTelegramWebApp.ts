'use client';

import { useEffect, useState, useCallback } from 'react';

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: {
    user?: {
      id: number;
      first_name: string;
      last_name?: string;
      username?: string;
      language_code?: string;
    };
    start_param?: string;
  };
  colorScheme: 'light' | 'dark';
  themeParams: {
    bg_color?: string;
    text_color?: string;
    hint_color?: string;
    link_color?: string;
    button_color?: string;
    button_text_color?: string;
  };
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  ready: () => void;
  expand: () => void;
  close: () => void;
  enableClosingConfirmation: () => void;
  disableClosingConfirmation: () => void;
  showPopup: (params: {
    title?: string;
    message: string;
    buttons?: Array<{ id?: string; type?: string; text: string }>;
  }) => void;
  showAlert: (message: string) => void;
  showConfirm: (message: string) => Promise<boolean>;
  openLink: (url: string) => void;
  openTelegramLink: (url: string) => void;
  openInvoice?: (url: string, callback?: (status: 'paid' | 'cancelled' | 'failed' | 'pending') => void) => void;
  HapticFeedback: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
    notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
    selectionChanged: () => void;
  };
  BackButton: {
    isVisible: boolean;
    show: () => void;
    hide: () => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
  };
  MainButton: {
    isVisible: boolean;
    isActive: boolean;
    text: string;
    color: string;
    textColor: string;
    isProgressVisible: boolean;
    show: () => void;
    hide: () => void;
    enable: () => void;
    disable: () => void;
    showProgress: (leaveActive?: boolean) => void;
    hideProgress: () => void;
    setText: (text: string) => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
  };
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

/**
 * Hook to access Telegram WebApp API
 * Initializes the WebApp on mount and provides typed access to all WebApp methods
 */
export function useTelegramWebApp() {
  const [webApp, setWebApp] = useState<TelegramWebApp | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const tg = window.Telegram?.WebApp;
    if (!tg) {
      if (process.env.NODE_ENV === 'development') {
        console.warn('Telegram WebApp not available. Running outside Telegram Mini App context.');
      }
      return;
    }

    // Initialize WebApp
    tg.ready();
    tg.expand();

    setWebApp(tg);
    setIsReady(true);

    // Apply Telegram theme colors to app
    if (tg.themeParams.bg_color) {
      document.documentElement.style.setProperty('--tg-bg-color', tg.themeParams.bg_color);
    }
    if (tg.themeParams.text_color) {
      document.documentElement.style.setProperty('--tg-text-color', tg.themeParams.text_color);
    }
  }, []);

  // Haptic feedback helpers
  const haptic = useCallback(
    (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' = 'medium') => {
      webApp?.HapticFeedback.impactOccurred(style);
    },
    [webApp]
  );

  const hapticNotification = useCallback(
    (type: 'error' | 'success' | 'warning') => {
      webApp?.HapticFeedback.notificationOccurred(type);
    },
    [webApp]
  );

  const hapticSelection = useCallback(() => {
    webApp?.HapticFeedback.selectionChanged();
  }, [webApp]);

  return {
    webApp,
    isReady,
    user: webApp?.initDataUnsafe.user,
    colorScheme: webApp?.colorScheme || 'dark',
    themeParams: webApp?.themeParams || {},
    haptic,
    hapticNotification,
    hapticSelection,
  };
}
