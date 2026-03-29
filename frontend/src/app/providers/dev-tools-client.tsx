'use client';

import { useEffect } from 'react';
import { DevPanel } from '@/features/dev/dev-panel';
import { consoleInterceptor } from '@/features/dev/lib/console-interceptor';
import { injectTwaMock } from '@/features/dev/lib/twa-mock';

export function DevToolsClient() {
  useEffect(() => {
    injectTwaMock();
    consoleInterceptor.start();

    return () => {
      consoleInterceptor.stop();
    };
  }, []);

  return <DevPanel />;
}
