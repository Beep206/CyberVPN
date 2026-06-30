import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanupTelegramWebAppMock, setupTelegramWebAppMock } from '@/test/mocks/telegram-webapp';
import { replaceMiniAppPath } from '../navigation';

describe('MiniApp document navigation fallback', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    cleanupTelegramWebAppMock();
    window.history.pushState({}, '', '/ru-RU/miniapp/onboarding/code?release=hotfix');
    vi.mocked(window.location.assign).mockClear();
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
    vi.useRealTimers();
  });

  it('uses localized document navigation when Telegram WebView client routing stalls', () => {
    setupTelegramWebAppMock();
    const router = { replace: vi.fn() };

    replaceMiniAppPath(router, '/miniapp/home', 'ru-RU');

    expect(router.replace).toHaveBeenCalledWith('/miniapp/home');
    vi.advanceTimersByTime(800);
    expect(window.location.assign).toHaveBeenCalledWith('/ru-RU/miniapp/home');
  });

  it('does not schedule document navigation outside Telegram WebView', () => {
    const router = { replace: vi.fn() };

    replaceMiniAppPath(router, '/miniapp/home', 'ru-RU');

    vi.advanceTimersByTime(800);
    expect(router.replace).toHaveBeenCalledWith('/miniapp/home');
    expect(window.location.assign).not.toHaveBeenCalled();
  });
});
