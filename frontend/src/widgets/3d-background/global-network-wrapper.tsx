'use client';

import dynamic from 'next/dynamic';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';
import { ErrorBoundary } from '@/shared/ui/error-boundary';

const GlobalNetworkScene = dynamic(() => import('@/3d/scenes/GlobalNetwork'), {
  ssr: false,
});

export function GlobalNetworkWrapper() {
  const { isReady } = useEnhancementReady({
    minimumTier: 'full',
    defer: 'idle',
  });

  if (!isReady) {
    return null;
  }

  return (
    <ErrorBoundary fallback={<div className="w-full h-full bg-terminal-bg flex items-center justify-center text-xs text-muted-foreground">3D Background Disabled (Extension Conflict)</div>}>
      <GlobalNetworkScene />
    </ErrorBoundary>
  );
}
