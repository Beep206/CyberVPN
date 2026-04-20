/**
 * Dashboard route-level loading skeleton.
 * Server Component — CSS-only animations, no JS hydration.
 * Shown by Next.js Suspense boundary during page navigation.
 */
export default function DashboardLoading() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading dashboard content">
      {/* Page title skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-48 rounded-xs bg-matrix-green/10" />
        <div className="h-6 w-24 rounded-xs bg-neon-cyan/10" />
      </div>

      {/* Stats row skeleton */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <div
            key={i}
            className="h-24 rounded-sm border border-grid-line bg-terminal-surface/50"
          >
            <div className="p-4 space-y-2">
              <div className="h-3 w-16 rounded-xs bg-neon-cyan/10" />
              <div className="h-6 w-20 rounded-xs bg-matrix-green/10" />
            </div>
          </div>
        ))}
      </div>

      {/* Data grid skeleton */}
      <div className="rounded-sm border border-grid-line bg-terminal-surface/50 overflow-hidden">
        {/* Table header */}
        <div className="flex gap-4 border-b border-grid-line px-4 py-3">
          {[120, 80, 160, 100, 60].map((w, i) => (
            <div
              key={i}
              className="h-3 rounded-xs bg-neon-cyan/10"
              style={{ width: `${w}px` }}
            />
          ))}
        </div>

        {/* Table rows */}
        {Array.from({ length: 6 }, (_, i) => (
          <div
            key={i}
            className="flex gap-4 border-b border-grid-line/50 px-4 py-3 last:border-b-0"
          >
            {[120, 80, 160, 100, 60].map((w, j) => (
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
