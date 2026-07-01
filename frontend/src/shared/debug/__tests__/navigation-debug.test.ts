import { afterEach, describe, expect, it, vi } from 'vitest';
import { installNavigationDebugLogger } from '../navigation-debug';

describe('installNavigationDebugLogger', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.restoreAllMocks();
    window.location.pathname = '/';
    delete process.env.NEXT_PUBLIC_NAV_DEBUG;
  });

  it('does not attach noisy document listeners unless explicitly enabled', () => {
    const debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});
    const cleanup = installNavigationDebugLogger();
    const anchor = document.createElement('a');
    anchor.href = 'http://localhost:3000/ru-RU/rewards/invites?token=secret';
    document.body.append(anchor);

    anchor.dispatchEvent(new MouseEvent('click', { bubbles: true, button: 0 }));

    expect(debugSpy).not.toHaveBeenCalled();
    cleanup();
  });

  it('logs only safe navigation metadata when debug mode is enabled', () => {
    process.env.NEXT_PUBLIC_NAV_DEBUG = 'true';
    window.location.pathname = '/ru-RU/dashboard';
    const debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});
    const cleanup = installNavigationDebugLogger();
    const anchor = document.createElement('a');
    anchor.href = 'http://localhost:3000/ru-RU/rewards/invites?token=secret';
    anchor.className = 'nav-link';
    document.body.append(anchor);

    anchor.dispatchEvent(new MouseEvent('click', { bubbles: true, button: 0 }));

    expect(debugSpy).toHaveBeenCalledWith(
      '[nav-debug]',
      expect.objectContaining({
        hrefPath: '/ru-RU/rewards/invites',
        type: 'click',
        viewportPath: '/ru-RU/dashboard',
      }),
    );
    expect(JSON.stringify(debugSpy.mock.calls)).not.toContain('token=secret');

    cleanup();
    anchor.dispatchEvent(new MouseEvent('click', { bubbles: true, button: 0 }));
    expect(debugSpy).toHaveBeenCalledTimes(1);
  });
});
