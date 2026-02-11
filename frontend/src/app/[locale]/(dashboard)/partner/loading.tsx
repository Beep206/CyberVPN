/**
 * Partner route-level loading skeleton.
 * Server Component — CSS-only animations, no JS hydration.
 * Shown by Next.js Suspense boundary during page navigation.
 */
export default function PartnerLoading() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading partner content">
      {/* Page title skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-56 rounded-xs bg-matrix-green/10" />
        <div className="h-6 w-24 rounded-xs bg-neon-cyan/10" />
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }, (_, i) => (
          <div
            key={i}
            className="h-28 rounded border border-grid-line bg-terminal-bg p-4"
          >
            <div className="space-y-3">
              <div className="h-3 w-20 rounded-xs bg-neon-cyan/10" />
              <div className="h-8 w-24 rounded-xs bg-matrix-green/10" />
              <div className="h-2 w-32 rounded-xs bg-foreground/5" />
            </div>
          </div>
        ))}
      </div>

      {/* Partner codes table */}
      <div className="rounded border border-grid-line bg-terminal-bg overflow-hidden">
        {/* Table header */}
        <div className="flex gap-4 border-b border-grid-line px-4 py-3">
          {[100, 80, 120, 90, 60].map((w, i) => (
            <div
              key={i}
              className="h-3 rounded-xs bg-neon-cyan/10"
              style={{ width: `${w}px` }}
            />
          ))}
        </div>

        {/* Table rows */}
        {Array.from({ length: 5 }, (_, i) => (
          <div
            key={i}
            className="flex gap-4 border-b border-grid-line/50 px-4 py-3 last:border-b-0"
          >
            {[100, 80, 120, 90, 60].map((w, j) => (
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
