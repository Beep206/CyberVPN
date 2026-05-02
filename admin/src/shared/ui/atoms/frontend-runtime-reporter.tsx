'use client';

import { usePathname } from 'next/navigation';
import { useEffect, useRef } from 'react';
import { reportFrontendRouteLoad, type FrontendSurface } from '@/shared/lib/frontend-observability';

export function FrontendRuntimeReporter({
  surface,
}: {
  surface: FrontendSurface;
}) {
  const pathname = usePathname();
  const lastReportedPathRef = useRef<string>('');

  useEffect(() => {
    if (!pathname) {
      return;
    }

    const routeKey = `${pathname}${typeof window !== 'undefined' ? window.location.search : ''}`;
    if (lastReportedPathRef.current === routeKey) {
      return;
    }

    lastReportedPathRef.current = routeKey;
    const startTime = performance.now();
    let firstFrame = 0;
    let secondFrame = 0;

    firstFrame = window.requestAnimationFrame(() => {
      secondFrame = window.requestAnimationFrame(() => {
        reportFrontendRouteLoad(surface, pathname, performance.now() - startTime);
      });
    });

    return () => {
      window.cancelAnimationFrame(firstFrame);
      window.cancelAnimationFrame(secondFrame);
    };
  }, [pathname, surface]);

  return null;
}
