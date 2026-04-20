import Link from 'next/link';

export function RouteNotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-terminal-bg p-4">
      <div className="max-w-2xl w-full border border-matrix-green bg-terminal-bg/90 backdrop-blur-sm rounded-sm p-8">
        {/* Header with glitch effect */}
        <div className="mb-6 text-center">
          <div className="font-cyber text-8xl text-matrix-green mb-2 animate-pulse">
            404
          </div>
          <div className="font-display text-2xl text-foreground mb-2">
            SIGNAL LOST
          </div>
          <div className="font-mono text-sm text-muted-foreground">
            REQUESTED COORDINATES NOT FOUND IN NETWORK
          </div>
        </div>

        {/* Terminal output */}
        <div className="mb-6 p-4 bg-black/50 border border-matrix-green/30 rounded-xs font-mono text-xs text-matrix-green">
          <div className="mb-1">&gt; SCANNING NETWORK...</div>
          <div className="mb-1">&gt; CHECKING BACKUP ROUTES...</div>
          <div className="mb-1">&gt; ERROR: DESTINATION UNREACHABLE</div>
          <div className="text-neon-red">&gt; STATUS: 404 NOT_FOUND</div>
        </div>

        {/* Action button */}
        <div className="flex justify-center">
          <Link
            href="/dashboard"
            className="px-8 py-4 bg-matrix-green text-black font-mono text-sm uppercase tracking-wider hover:bg-matrix-green/80 transition-colors border border-matrix-green hover:shadow-[0_0_20px_rgba(0,255,136,0.5)] rounded-xs focus:outline-hidden focus:ring-2 focus:ring-matrix-green"
          >
            Return to Base
          </Link>
        </div>

        {/* Terminal decoration */}
        <div className="mt-6 pt-6 border-t border-matrix-green/20 text-center text-xs text-muted-foreground font-mono">
          [PRESS ANY KEY TO CONTINUE]
        </div>
      </div>
    </div>
  );
}
