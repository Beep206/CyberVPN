/**
 * Wallet route-level loading skeleton.
 * Server Component — CSS-only animations, no JS hydration.
 * Shown by Next.js Suspense boundary during page navigation.
 */
export default function WalletLoading() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading wallet content">
      {/* Page title skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-40 rounded-xs bg-matrix-green/10" />
      </div>

      {/* Balance card */}
      <div className="h-48 rounded border border-grid-line bg-terminal-bg p-6">
        <div className="space-y-6">
          <div className="space-y-2">
            <div className="h-4 w-32 rounded-xs bg-neon-cyan/10" />
            <div className="h-12 w-48 rounded-xs bg-matrix-green/10" />
          </div>
          <div className="flex gap-2">
            <div className="h-10 w-32 rounded border border-grid-line bg-grid-line/20" />
            <div className="h-10 w-32 rounded border border-grid-line bg-grid-line/20" />
          </div>
        </div>
      </div>

      {/* Transactions table */}
      <div className="rounded border border-grid-line bg-terminal-bg overflow-hidden">
        {/* Table header */}
        <div className="flex gap-4 border-b border-grid-line px-4 py-3">
          {[120, 140, 100, 80, 90].map((w, i) => (
            <div
              key={i}
              className="h-3 rounded-xs bg-neon-cyan/10"
              style={{ width: `${w}px` }}
            />
          ))}
        </div>

        {/* Table rows */}
        {Array.from({ length: 8 }, (_, i) => (
          <div
            key={i}
            className="flex gap-4 border-b border-grid-line/50 px-4 py-3 last:border-b-0"
          >
            {[120, 140, 100, 80, 90].map((w, j) => (
              <div
                key={j}
                className="h-3 rounded-xs bg-foreground/5"
                style={{ width: `${w}px` }}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
