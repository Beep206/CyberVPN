/**
 * Mock Telegram WebApp SDK for testing
 *
 * Provides a complete mock implementation of window.Telegram.WebApp
 * for use in vitest tests.
 */

import { vi } from 'vitest';

export interface TelegramWebAppMock {
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
  ready: ReturnType<typeof vi.fn>;
  expand: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
  enableClosingConfirmation: ReturnType<typeof vi.fn>;
  disableClosingConfirmation: ReturnType<typeof vi.fn>;
  showPopup: ReturnType<typeof vi.fn>;
  showAlert: ReturnType<typeof vi.fn>;
  showConfirm: ReturnType<typeof vi.fn>;
  openLink: ReturnType<typeof vi.fn>;
  openTelegramLink: ReturnType<typeof vi.fn>;
  HapticFeedback: {
    impactOccurred: ReturnType<typeof vi.fn>;
    notificationOccurred: ReturnType<typeof vi.fn>;
    selectionChanged: ReturnType<typeof vi.fn>;
  };
  BackButton: {
    isVisible: boolean;
    show: ReturnType<typeof vi.fn>;
    hide: ReturnType<typeof vi.fn>;
    onClick: ReturnType<typeof vi.fn>;
    offClick: ReturnType<typeof vi.fn>;
  };
  MainButton: {
    isVisible: boolean;
    isActive: boolean;
    text: string;
    color: string;
    textColor: string;
    isProgressVisible: boolean;
    show: ReturnType<typeof vi.fn>;
    hide: ReturnType<typeof vi.fn>;
    enable: ReturnType<typeof vi.fn>;
    disable: ReturnType<typeof vi.fn>;
    showProgress: ReturnType<typeof vi.fn>;
    hideProgress: ReturnType<typeof vi.fn>;
    setText: ReturnType<typeof vi.fn>;
    onClick: ReturnType<typeof vi.fn>;
    offClick: ReturnType<typeof vi.fn>;
  };
}

/**
 * Create a mock Telegram WebApp instance
 */
export function createTelegramWebAppMock(overrides?: Partial<TelegramWebAppMock>): TelegramWebAppMock {
  const defaultMock: TelegramWebAppMock = {
    initData: 'mock_init_data',
    initDataUnsafe: {
      user: {
        id: 123456789,
        first_name: 'Test',
        last_name: 'User',
        username: 'testuser',
        language_code: 'en',
      },
      start_param: undefined,
    },
    colorScheme: 'dark',
    themeParams: {
      bg_color: '#1a1a1a',
      text_color: '#ffffff',
      hint_color: '#aaaaaa',
      link_color: '#00ffff',
      button_color: '#00ff88',
      button_text_color: '#000000',
    },
    isExpanded: true,
    viewportHeight: 800,
    viewportStableHeight: 800,
    ready: vi.fn(),
    expand: vi.fn(),
    close: vi.fn(),
    enableClosingConfirmation: vi.fn(),
    disableClosingConfirmation: vi.fn(),
    showPopup: vi.fn(),
    showAlert: vi.fn(),
    showConfirm: vi.fn().mockResolvedValue(true),
    openLink: vi.fn(),
    openTelegramLink: vi.fn(),
    HapticFeedback: {
      impactOccurred: vi.fn(),
      notificationOccurred: vi.fn(),
      selectionChanged: vi.fn(),
    },
    BackButton: {
      isVisible: false,
      show: vi.fn(),
      hide: vi.fn(),
      onClick: vi.fn(),
      offClick: vi.fn(),
    },
    MainButton: {
      isVisible: false,
      isActive: false,
      text: '',
      color: '#00ff88',
      textColor: '#000000',
      isProgressVisible: false,
      show: vi.fn(),
      hide: vi.fn(),
      enable: vi.fn(),
      disable: vi.fn(),
      showProgress: vi.fn(),
      hideProgress: vi.fn(),
      setText: vi.fn(),
      onClick: vi.fn(),
      offClick: vi.fn(),
    },
  };

  return { ...defaultMock, ...overrides };
}

/**
 * Setup Telegram WebApp mock on window object
 */
export function setupTelegramWebAppMock(overrides?: Partial<TelegramWebAppMock>) {
  const mock = createTelegramWebAppMock(overrides);

  Object.defineProperty(window, 'Telegram', {
    writable: true,
    configurable: true,
    value: {
      WebApp: mock,
    },
  });

  return mock;
}

/**
 * Clean up Telegram WebApp mock
 */
export function cleanupTelegramWebAppMock() {
  delete (window as any).Telegram;
}
