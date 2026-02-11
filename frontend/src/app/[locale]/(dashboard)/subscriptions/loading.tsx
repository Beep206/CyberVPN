/**
 * Subscriptions route-level loading skeleton.
 * Server Component — CSS-only animations, no JS hydration.
 * Shown by Next.js Suspense boundary during page navigation.
 */
export default function SubscriptionsLoading() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading subscriptions content">
      {/* Page title skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-48 rounded-xs bg-matrix-green/10" />
        <div className="h-6 w-24 rounded-xs bg-neon-cyan/10" />
      </div>

      {/* Active subscription card */}
      <div className="h-40 rounded border border-grid-line bg-terminal-bg p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="h-5 w-40 rounded-xs bg-neon-cyan/10" />
            <div className="h-4 w-20 rounded-xs bg-matrix-green/10" />
          </div>
          <div className="space-y-2">
            <div className="h-3 w-32 rounded-xs bg-foreground/5" />
            <div className="h-3 w-28 rounded-xs bg-foreground/5" />
          </div>
          <div className="h-10 w-32 rounded border border-grid-line bg-grid-line/20" />
        </div>
      </div>

      {/* Plan cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }, (_, i) => (
          <div
            key={i}
            className="h-80 rounded border border-grid-line bg-terminal-bg p-6"
          >
            <div className="space-y-4">
              <div className="h-6 w-24 rounded-xs bg-neon-cyan/10" />
              <div className="h-8 w-32 rounded-xs bg-matrix-green/10" />
              <div className="space-y-2">
                {Array.from({ length: 4 }, (_, j) => (
                  <div key={j} className="h-3 w-full rounded-xs bg-foreground/5" />
                ))}
              </div>
              <div className="h-10 w-full rounded border border-grid-line bg-grid-line/20" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
