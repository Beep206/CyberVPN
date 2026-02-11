/**
 * Settings route-level loading skeleton.
 * Server Component — CSS-only animations, no JS hydration.
 * Shown by Next.js Suspense boundary during page navigation.
 */
export default function SettingsLoading() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading settings content">
      {/* Page title skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-32 rounded-xs bg-matrix-green/10" />
      </div>

      {/* Settings sections */}
      <div className="space-y-6">
        {Array.from({ length: 3 }, (_, i) => (
          <div
            key={i}
            className="rounded border border-grid-line bg-terminal-bg p-6"
          >
            <div className="space-y-4">
              {/* Section title */}
              <div className="h-5 w-40 rounded-xs bg-neon-cyan/10" />

              {/* Form fields */}
              <div className="space-y-4">
                {Array.from({ length: 3 }, (_, j) => (
                  <div key={j} className="space-y-2">
                    <div className="h-3 w-24 rounded-xs bg-foreground/5" />
                    <div className="h-10 w-full rounded border border-grid-line bg-grid-line/20" />
                  </div>
                ))}
              </div>

              {/* Action buttons */}
              <div className="flex gap-2">
                <div className="h-10 w-24 rounded border border-grid-line bg-grid-line/20" />
                <div className="h-10 w-20 rounded border border-grid-line bg-grid-line/20" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
