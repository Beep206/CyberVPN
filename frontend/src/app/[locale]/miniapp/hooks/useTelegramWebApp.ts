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
    secondary_bg_color?: string;
    text_color?: string;
    hint_color?: string;
    link_color?: string;
    button_color?: string;
    button_text_color?: string;
    header_bg_color?: string;
    section_bg_color?: string;
    section_header_text_color?: string;
    subtitle_text_color?: string;
    destructive_text_color?: string;
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
  showConfirm: (message: string, callback?: (confirmed: boolean) => void) => void | boolean | Promise<boolean>;
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
  onEvent?: (eventType: 'themeChanged', callback: () => void) => void;
  offEvent?: (eventType: 'themeChanged', callback: () => void) => void;
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

  /* eslint-disable react-hooks/set-state-in-effect -- Telegram SDK init requires setting state after expand */
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const tg = window.Telegram?.WebApp;
    if (!tg) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Telegram WebApp not available. Running outside Telegram Mini App context.');
      }
      return;
    }

    const applyTelegramTheme = () => {
      const root = document.documentElement;
      const themeParams = tg.themeParams || {};
      const cssVariableMap: Record<keyof TelegramWebApp['themeParams'], string[]> = {
        bg_color: ['--tg-theme-bg-color', '--tg-bg-color'],
        secondary_bg_color: ['--tg-theme-secondary-bg-color', '--tg-secondary-bg-color'],
        text_color: ['--tg-theme-text-color', '--tg-text-color'],
        hint_color: ['--tg-theme-hint-color', '--tg-hint-color'],
        link_color: ['--tg-theme-link-color', '--tg-link-color'],
        button_color: ['--tg-theme-button-color', '--tg-button-color'],
        button_text_color: ['--tg-theme-button-text-color', '--tg-button-text-color'],
        header_bg_color: ['--tg-theme-header-bg-color'],
        section_bg_color: ['--tg-theme-section-bg-color'],
        section_header_text_color: ['--tg-theme-section-header-text-color'],
        subtitle_text_color: ['--tg-theme-subtitle-text-color'],
        destructive_text_color: ['--tg-theme-destructive-text-color'],
      };

      for (const [key, variableNames] of Object.entries(cssVariableMap) as Array<[
        keyof TelegramWebApp['themeParams'],
        string[],
      ]>) {
        const value = themeParams[key];
        if (!value) continue;
        for (const variableName of variableNames) {
          root.style.setProperty(variableName, value);
        }
      }

      root.dataset.telegramColorScheme = tg.colorScheme;
    };

    // Initialize WebApp
    tg.ready();
    tg.expand();
    applyTelegramTheme();
    tg.onEvent?.('themeChanged', applyTelegramTheme);

    setWebApp(tg);
    setIsReady(true);

    return () => {
      tg.offEvent?.('themeChanged', applyTelegramTheme);
    };
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

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
