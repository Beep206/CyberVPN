'use client';

import * as Sentry from '@sentry/nextjs';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { AlertCircle, Copy, Check, RotateCcw, Home, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface RouteErrorBoundaryProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export function RouteErrorBoundary({ error, reset }: RouteErrorBoundaryProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  const handleCopy = async () => {
    const textToCopy = `Error Code: ${error.digest || 'UNKNOWN'}\nMessage: ${error.message}\nStack: ${error.stack || 'N/A'}`;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy error:', err);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-terminal-bg p-4 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 pointer-events-none opacity-20">
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-neon-red to-transparent" />
        <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-neon-red to-transparent" />
      </div>

      <div className="max-w-2xl w-full border border-neon-red/50 bg-terminal-bg/95 backdrop-blur-xl rounded-lg shadow-[0_0_50px_rgba(255,0,76,0.15)] p-6 md:p-8 flex flex-col gap-6 relative z-10">
        {/* Header with glitch effect */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-neon-red/10 border border-neon-red/20 mb-4 animate-pulse">
            <AlertCircle className="w-8 h-8 text-neon-red" />
          </div>
          <h1 className="font-cyber text-4xl md:text-5xl text-neon-red tracking-tight">
            SYSTEM FAILURE
          </h1>
          <p className="font-mono text-sm text-muted-foreground uppercase tracking-widest">
            Critical Error Detected
          </p>
        </div>

        {/* Error Details Card */}
        <div className="relative group bg-black/40 border border-neon-red/20 rounded-md overflow-hidden transition-all hover:border-neon-red/40">
          <div className="flex items-center justify-between p-3 border-b border-neon-red/10 bg-neon-red/5">
            <span className="font-mono text-xs text-neon-red font-bold">
              ERROR_LOG: {error.digest || 'UNKNOWN'}
            </span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono rounded-sm transition-all hover:bg-neon-red/20 text-muted-foreground hover:text-neon-red focus:outline-none focus:ring-1 focus:ring-neon-red"
              title="Copy error details"
            >
              {isCopied ? (
                <>
                  <Check className="w-3 h-3" />
                  <span>COPIED</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>COPY LOG</span>
                </>
              )}
            </button>
          </div>

          <div
            className={cn(
              "p-4 font-mono text-sm text-gray-300 whitespace-pre-wrap break-words transition-all duration-300 ease-in-out",
              isExpanded ? "max-h-[60vh] overflow-y-auto custom-scrollbar" : "max-h-32 overflow-hidden relative"
            )}
          >
            <div className="space-y-2">
              <p><span className="text-neon-red">Message:</span> {error.message || 'An unexpected error occurred'}</p>
              {error.stack && (
                <div className="mt-4 pt-4 border-t border-white/10 text-xs text-gray-500">
                  <p className="text-neon-red mb-1">Stack Trace:</p>
                  {error.stack}
                </div>
              )}
            </div>

            {!isExpanded && (
              <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-black/90 to-transparent pointer-events-none" />
            )}
          </div>

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center justify-center gap-2 p-2 text-xs font-mono text-muted-foreground hover:text-white bg-white/5 hover:bg-white/10 transition-colors border-t border-neon-red/10"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-3 h-3" />
                COLLAPSE LOG
              </>
            ) : (
              <>
                <ChevronDown className="w-3 h-3" />
                EXPAND FULL LOG
              </>
            )}
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-4">
          <Button
            onClick={reset}
            className="h-12 px-8 bg-neon-red hover:bg-neon-red/80 text-white font-bold font-mono uppercase tracking-wider shadow-[0_0_15px_rgba(255,0,76,0.3)] hover:shadow-[0_0_25px_rgba(255,0,76,0.5)] border-0 transition-all hover:scale-[1.02] min-w-[200px]"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reboot System
          </Button>

          <Link href="/dashboard" passHref legacyBehavior>
            <Button
              variant="outline"
              className="h-12 px-8 border-neon-cyan/50 text-neon-cyan hover:bg-neon-cyan/10 hover:text-neon-cyan font-bold font-mono uppercase tracking-wider hover:shadow-[0_0_15px_rgba(0,255,255,0.2)] transition-all hover:scale-[1.02] min-w-[200px]"
            >
              <Home className="w-4 h-4 mr-2" />
              Return to Base
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
