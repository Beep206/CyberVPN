/**
 * Users route-level loading skeleton.
 * Server Component — CSS-only animations, no JS hydration.
 * Shown by Next.js Suspense boundary during page navigation.
 */
export default function UsersLoading() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading users content">
      {/* Page title skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-32 rounded-xs bg-matrix-green/10" />
        <div className="h-6 w-20 rounded-xs bg-neon-cyan/10" />
      </div>

      {/* Search and filter bar */}
      <div className="flex gap-4">
        <div className="h-10 flex-1 rounded border border-grid-line bg-terminal-bg" />
        <div className="h-10 w-40 rounded border border-grid-line bg-terminal-bg" />
        <div className="h-10 w-32 rounded border border-grid-line bg-terminal-bg" />
      </div>

      {/* Users table */}
      <div className="rounded border border-grid-line bg-terminal-bg overflow-hidden">
        {/* Table header */}
        <div className="flex gap-4 border-b border-grid-line px-4 py-3">
          {[140, 120, 100, 80, 70, 60].map((w, i) => (
            <div
              key={i}
              className="h-3 rounded-xs bg-neon-cyan/10"
              style={{ width: `${w}px` }}
            />
          ))}
        </div>

        {/* Table rows */}
        {Array.from({ length: 10 }, (_, i) => (
          <div
            key={i}
            className="flex gap-4 border-b border-grid-line/50 px-4 py-3 last:border-b-0"
          >
            {[140, 120, 100, 80, 70, 60].map((w, j) => (
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
