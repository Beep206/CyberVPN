'use client';

import { useEffect, useRef } from 'react';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';

interface LenisController {
  destroy: () => void;
  start: () => void;
  stop: () => void;
}

export function SmoothScrollProvider() {
  const lenisRef = useRef<LenisController | null>(null);
  const { isReady } = useEnhancementReady({
    minimumTier: 'full',
    defer: 'idle',
  });

  useEffect(() => {
    if (!isReady || typeof window === 'undefined') {
      return;
    }

    let isActive = true;
    let stopLenis: (() => void) | undefined;
    let startLenis: (() => void) | undefined;

    void import('lenis').then(({ default: Lenis }) => {
      if (!isActive) {
        return;
      }

      const lenis = new Lenis({
        duration: 1.2,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        orientation: 'vertical',
        gestureOrientation: 'vertical',
        smoothWheel: true,
        wheelMultiplier: 1,
        touchMultiplier: 2,
        autoRaf: true,
      });

      lenisRef.current = lenis;
      stopLenis = () => lenis.stop();
      startLenis = () => lenis.start();
      window.addEventListener('lenis:stop', stopLenis);
      window.addEventListener('lenis:start', startLenis);
    });

    return () => {
      isActive = false;

      if (stopLenis) {
        window.removeEventListener('lenis:stop', stopLenis);
      }

      if (startLenis) {
        window.removeEventListener('lenis:start', startLenis);
      }

      lenisRef.current?.destroy();
      lenisRef.current = null;
    };
  }, [isReady]);

  return null;
}
