/**
 * Dashboard overview route-level loading skeleton.
 * Server Component — CSS-only animations, no JS hydration.
 * Shown by Next.js Suspense boundary during page navigation.
 */
export default function DashboardLoading() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading dashboard content">
      {/* Page title skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-40 rounded-xs bg-matrix-green/10" />
        <div className="h-6 w-32 rounded-xs bg-neon-cyan/10" />
      </div>

      {/* Stats row skeleton */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <div
            key={i}
            className="h-24 rounded border border-grid-line bg-terminal-bg"
          >
            <div className="p-4 space-y-2">
              <div className="h-3 w-24 rounded-xs bg-neon-cyan/10" />
              <div className="h-6 w-16 rounded-xs bg-matrix-green/10" />
            </div>
          </div>
        ))}
      </div>

      {/* Activity feed skeleton */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded border border-grid-line bg-terminal-bg p-6">
          <div className="space-y-4">
            <div className="h-5 w-32 rounded-xs bg-neon-cyan/10" />
            {Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="flex items-center gap-3 py-3">
                <div className="h-10 w-10 rounded-full bg-matrix-green/10" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-3/4 rounded-xs bg-grid-line/40" />
                  <div className="h-2 w-1/2 rounded-xs bg-grid-line/20" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Chart placeholder */}
        <div className="rounded border border-grid-line bg-terminal-bg p-6">
          <div className="space-y-4">
            <div className="h-4 w-32 rounded-xs bg-neon-cyan/10" />
            <div className="h-64 rounded-xs bg-grid-line/20" />
          </div>
        </div>
      </div>
    </div>
  );
}
