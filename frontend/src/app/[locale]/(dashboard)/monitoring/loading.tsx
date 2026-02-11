/**
 * Monitoring route-level loading skeleton.
 * Server Component — CSS-only animations, no JS hydration.
 * Shown by Next.js Suspense boundary during page navigation.
 */
export default function MonitoringLoading() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading monitoring content">
      {/* Page title skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-48 rounded-xs bg-matrix-green/10" />
        <div className="h-6 w-20 rounded-xs bg-neon-cyan/10" />
      </div>

      {/* Service status grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }, (_, i) => (
          <div
            key={i}
            className="h-32 rounded border border-grid-line bg-terminal-bg p-4"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="h-4 w-24 rounded-xs bg-neon-cyan/10" />
                <div className="h-3 w-16 rounded-xs bg-matrix-green/10" />
              </div>
              <div className="h-2 w-full rounded-xs bg-grid-line/20" />
              <div className="flex gap-2">
                <div className="h-3 w-12 rounded-xs bg-foreground/5" />
                <div className="h-3 w-16 rounded-xs bg-foreground/5" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Bandwidth chart */}
      <div className="h-96 rounded border border-grid-line bg-terminal-bg p-6">
        <div className="space-y-4">
          <div className="h-4 w-40 rounded-xs bg-neon-cyan/10" />
          <div className="h-80 rounded-xs bg-grid-line/20" />
        </div>
      </div>
    </div>
  );
}
