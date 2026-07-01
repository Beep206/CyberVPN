'use client';

import { useEffect } from 'react';
import { consoleInterceptor } from '@/features/dev/lib/console-interceptor';
import { cssXRay } from '@/features/dev/lib/css-xray';
import { networkLogger } from '@/features/dev/lib/network-logger';
import { renderProfiler } from '@/features/dev/lib/render-profiler';
import { injectTwaMock } from '@/features/dev/lib/twa-mock';

export function DevToolsBootstrap() {
  useEffect(() => {
    if (
      process.env.NODE_ENV !== 'development' ||
      process.env.NEXT_PUBLIC_DEV_TOOLS_ENABLED !== 'true'
    ) {
      return undefined;
    }

    const restoreTwaMock = injectTwaMock();
    consoleInterceptor.start();
    networkLogger.start();
    renderProfiler.start();
    cssXRay.start();

    const savedMocks = localStorage.getItem('DEV_MOCK_RULES');
    if (savedMocks) {
      try {
        networkLogger.mockRules = JSON.parse(savedMocks);
      } catch {
        // Ignore malformed persisted mocks in dev mode.
      }
    }

    const legacyMocks = localStorage.getItem('dev_mock_rules');
    if (legacyMocks) {
      try {
        networkLogger.mockRules = JSON.parse(legacyMocks);
      } catch {
        // Ignore malformed legacy persisted mocks in dev mode.
      }
    }

    if (localStorage.getItem('DEV_RTL') === 'true') {
      document.documentElement.dir = 'rtl';
    }

    const savedTheme = localStorage.getItem('DEV_CUSTOM_THEME');
    if (savedTheme) {
      try {
        const theme = JSON.parse(savedTheme) as Record<string, string>;

        Object.entries(theme).forEach(([key, value]) => {
          if (value) {
            document.documentElement.style.setProperty(key, value);
          }
        });
      } catch {
        // Ignore malformed persisted theme overrides in dev mode.
      }
    }

    return () => {
      restoreTwaMock();
      consoleInterceptor.stop();
      networkLogger.stop();
      renderProfiler.stop();
      cssXRay.stop();
    };
  }, []);

  return null;
}
