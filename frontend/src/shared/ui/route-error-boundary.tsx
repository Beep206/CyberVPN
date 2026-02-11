'use client';

import * as Sentry from '@sentry/nextjs';
import { useEffect } from 'react';
import Link from 'next/link';

interface RouteErrorBoundaryProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export function RouteErrorBoundary({ error, reset }: RouteErrorBoundaryProps) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-terminal-bg p-4">
      <div className="max-w-2xl w-full border border-neon-red bg-terminal-bg/90 backdrop-blur-sm rounded-sm p-8">
        {/* Header with glitch effect */}
        <div className="mb-6 text-center">
          <div className="font-cyber text-6xl text-neon-red mb-2 animate-pulse">
            ERROR
          </div>
          <div className="font-mono text-sm text-muted-foreground">
            SYSTEM MALFUNCTION DETECTED
          </div>
        </div>

        {/* Error details */}
        <div className="mb-6 p-4 bg-black/50 border border-neon-red/30 rounded-xs font-mono text-xs">
          <div className="text-neon-red mb-2">
            &gt; ERROR_CODE: {error.digest || 'UNKNOWN'}
          </div>
          <div className="text-muted-foreground line-clamp-3">
            &gt; MESSAGE: {error.message || 'An unexpected error occurred'}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={reset}
            className="flex-1 px-6 py-3 bg-neon-red text-black font-mono text-sm uppercase tracking-wider hover:bg-neon-red/80 transition-colors border border-neon-red hover:shadow-[0_0_20px_rgba(255,0,76,0.5)] rounded-xs focus:outline-hidden focus:ring-2 focus:ring-neon-red"
          >
            Try Again
          </button>
          <Link
            href="/dashboard"
            className="flex-1 px-6 py-3 bg-neon-cyan text-black font-mono text-sm uppercase tracking-wider hover:bg-neon-cyan/80 transition-colors border border-neon-cyan hover:shadow-[0_0_20px_rgba(0,255,255,0.5)] rounded-xs text-center focus:outline-hidden focus:ring-2 focus:ring-neon-cyan"
          >
            Go Home
          </Link>
        </div>

        {/* Terminal decoration */}
        <div className="mt-6 pt-6 border-t border-neon-red/20 text-center text-xs text-muted-foreground font-mono">
          [REPORT LOGGED TO MONITORING SYSTEM]
        </div>
      </div>
    </div>
  );
}
