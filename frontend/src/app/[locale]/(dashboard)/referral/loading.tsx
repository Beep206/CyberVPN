/**
 * Referral route-level loading skeleton.
 * Server Component — CSS-only animations, no JS hydration.
 * Shown by Next.js Suspense boundary during page navigation.
 */
export default function ReferralLoading() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading referral content">
      {/* Page title skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-44 rounded-xs bg-matrix-green/10" />
        <div className="h-6 w-28 rounded-xs bg-neon-cyan/10" />
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <div
            key={i}
            className="h-24 rounded border border-grid-line bg-terminal-bg p-4"
          >
            <div className="space-y-2">
              <div className="h-3 w-20 rounded-xs bg-neon-cyan/10" />
              <div className="h-6 w-16 rounded-xs bg-matrix-green/10" />
            </div>
          </div>
        ))}
      </div>

      {/* Invite link card */}
      <div className="h-32 rounded border border-grid-line bg-terminal-bg p-6">
        <div className="space-y-4">
          <div className="h-4 w-32 rounded-xs bg-neon-cyan/10" />
          <div className="flex gap-2">
            <div className="h-10 flex-1 rounded border border-grid-line bg-grid-line/20" />
            <div className="h-10 w-24 rounded border border-grid-line bg-grid-line/20" />
          </div>
        </div>
      </div>

      {/* Referral table */}
      <div className="rounded border border-grid-line bg-terminal-bg overflow-hidden">
        {/* Table header */}
        <div className="flex gap-4 border-b border-grid-line px-4 py-3">
          {[120, 100, 80, 90, 70].map((w, i) => (
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
            {[120, 100, 80, 90, 70].map((w, j) => (
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
