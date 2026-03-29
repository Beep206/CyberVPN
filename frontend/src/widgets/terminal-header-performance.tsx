'use client';

import { useEffect, useState, useRef } from 'react';

interface TerminalHeaderPerformanceProps {
  mode?: 'off' | 'idle' | 'always';
  fpsLabel: string;
  pingLabel: string;
}

export function TerminalHeaderPerformance({
  mode = 'off',
  fpsLabel,
  pingLabel,
}: TerminalHeaderPerformanceProps) {
  const fpsRef = useRef<HTMLSpanElement>(null);
  const pingRef = useRef<HTMLSpanElement>(null);
  const [isIdleActive, setIsIdleActive] = useState(false);
  const isActive = mode === 'always' || (mode === 'idle' && isIdleActive);
  const isPendingActivation = mode === 'idle' && !isActive;

  useEffect(() => {
    if (mode !== 'idle') {
      return;
    }

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let idleId: number | null = null;

    const activate = () => {
      if (!cancelled) {
        setIsIdleActive(true);
      }
    };

    timeoutId = setTimeout(activate, 2500);

    if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
      idleId = window.requestIdleCallback(activate, { timeout: 2500 });
    }

    return () => {
      cancelled = true;

      if (timeoutId) {
        clearTimeout(timeoutId);
      }

      if (idleId !== null && typeof window !== 'undefined' && 'cancelIdleCallback' in window) {
        window.cancelIdleCallback(idleId);
      }
    };
  }, [mode]);

  useEffect(() => {
    if (!isActive) {
      return;
    }

    let frameCount = 0;
    let lastTime = performance.now();
    let rafId = 0;

    const countFrame = () => {
      if (document.hidden) {
        rafId = requestAnimationFrame(countFrame);
        return;
      }

      frameCount += 1;
      rafId = requestAnimationFrame(countFrame);
    };

    rafId = requestAnimationFrame(countFrame);

    const display = setInterval(() => {
      if (document.hidden) {
        return;
      }

      const now = performance.now();
      const delta = now - lastTime;

      if (delta > 0 && fpsRef.current) {
        fpsRef.current.textContent = String(Math.round((frameCount * 1000) / delta));
      }

      frameCount = 0;
      lastTime = now;
    }, 1000);

    return () => {
      cancelAnimationFrame(rafId);
      clearInterval(display);
    };
  }, [isActive]);

  useEffect(() => {
    if (!isActive) {
      return;
    }

    let active = true;

    const measurePing = async () => {
      if (document.hidden) {
        return;
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      const start = performance.now();

      try {
        await fetch('/favicon.ico', {
          method: 'HEAD',
          cache: 'no-store',
          signal: controller.signal,
        });
      } catch {
        // Ignore aborts and transient network errors.
      }

      clearTimeout(timeoutId);

      if (active && pingRef.current) {
        pingRef.current.textContent = `${Math.round(performance.now() - start)}ms`;
      }
    };

    void measurePing();
    const interval = setInterval(() => {
      void measurePing();
    }, 30000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [isActive]);

  if (mode === 'off') {
    return null;
  }

  return (
    <div className={`hidden md:flex items-center gap-3 text-[11px] font-mono min-w-[102px] transition-opacity duration-500 ${isPendingActivation ? 'opacity-60 text-muted-foreground' : 'opacity-100 text-muted-foreground'}`}>
      <div className="flex items-center gap-1">
        <span className="text-muted-foreground-low">{fpsLabel}</span>
        <span ref={fpsRef} className={`transition-colors duration-500 ${isPendingActivation ? 'text-muted-foreground-low' : 'text-neon-cyan'}`}>--</span>
      </div>
      <span className="text-muted-foreground-low">|</span>
      <div className="flex items-center gap-1">
        <span className="text-muted-foreground-low">{pingLabel}</span>
        <span ref={pingRef} className={`transition-colors duration-500 ${isPendingActivation ? 'text-muted-foreground-low' : 'text-matrix-green'}`}>--</span>
      </div>
    </div>
  );
}
