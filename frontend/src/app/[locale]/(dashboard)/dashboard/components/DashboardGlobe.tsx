'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';
import { useVisualTier } from '@/shared/hooks/use-visual-tier';
import { ErrorBoundary } from '@/shared/ui/error-boundary';

const GlobalNetworkScene = dynamic(() => import('@/3d/scenes/GlobalNetwork'), {
  ssr: false,
  loading: () => null,
});

const IDLE_TIMEOUT_MS = 1_500;

function StaticNetworkBackdrop({ visualTier }: { visualTier: 'minimal' | 'reduced' | 'full' }) {
  if (visualTier === 'full') {
    return null;
  }

  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(0,255,255,0.12),transparent_22%),radial-gradient(circle_at_75%_30%,rgba(0,255,136,0.14),transparent_20%),linear-gradient(160deg,rgba(0,0,0,0)_0%,rgba(0,12,18,0.42)_55%,rgba(0,0,0,0.18)_100%)]"
    >
      <div className="absolute inset-x-12 top-20 h-px bg-gradient-to-r from-transparent via-neon-cyan/40 to-transparent" />
      <div className="absolute inset-x-20 bottom-28 h-px bg-gradient-to-r from-transparent via-matrix-green/35 to-transparent" />
      {visualTier === 'reduced' ? (
        <>
          <div className="absolute left-[18%] top-[28%] h-20 w-20 rounded-full border border-neon-cyan/30 shadow-[0_0_30px_rgba(0,255,255,0.08)]" />
          <div className="absolute right-[22%] top-[42%] h-28 w-28 rounded-full border border-matrix-green/25" />
          <div className="absolute bottom-[18%] left-[46%] h-16 w-16 rounded-full border border-neon-cyan/20" />
        </>
      ) : null}
    </div>
  );
}

export function DashboardGlobe() {
  const { tier: visualTier, isFull } = useVisualTier();
  const [isGlobeReady, setIsGlobeReady] = useState(false);

  useEffect(() => {
    const win = window as Window & {
      requestIdleCallback?: (callback: () => void, options?: { timeout: number }) => number;
      cancelIdleCallback?: (handle: number) => void;
    };

    if (!isFull) {
      return () => {};
    }

    const activate = () => {
      setIsGlobeReady(true);
    };

    if (win.requestIdleCallback) {
      const handle = win.requestIdleCallback(activate, { timeout: IDLE_TIMEOUT_MS });
      return () => {
        win.cancelIdleCallback?.(handle);
      };
    }

    const timeoutId = window.setTimeout(activate, 200);
    return () => window.clearTimeout(timeoutId);
  }, [isFull]);

  const showGlobe = isFull && isGlobeReady;

  return (
    <>
      <div
        aria-hidden="true"
        data-visual-tier={visualTier}
        className="fixed inset-0 z-0 pointer-events-none md:pl-64"
      >
        {showGlobe ? (
          <ErrorBoundary label="3D Globe" fallback={null}>
            <GlobalNetworkScene />
          </ErrorBoundary>
        ) : (
          <StaticNetworkBackdrop visualTier={visualTier} />
        )}
      </div>

      <div
        aria-hidden="true"
        className={
          visualTier === 'full'
            ? 'fixed inset-0 z-0 pointer-events-none bg-gradient-to-br from-terminal-bg/90 via-terminal-bg/80 to-terminal-bg/40 md:pl-64'
            : 'fixed inset-0 z-0 pointer-events-none bg-gradient-to-br from-terminal-bg/96 via-terminal-bg/88 to-terminal-bg/55 md:pl-64'
        }
      />
    </>
  );
}
