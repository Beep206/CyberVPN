/**
 * Payment History route-level loading skeleton.
 * Server Component — CSS-only animations, no JS hydration.
 * Shown by Next.js Suspense boundary during page navigation.
 */
export default function PaymentHistoryLoading() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading payment history content">
      {/* Page title skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-52 rounded-xs bg-matrix-green/10" />
      </div>

      {/* Filter bar */}
      <div className="flex gap-4">
        <div className="h-10 w-48 rounded border border-grid-line bg-terminal-bg" />
        <div className="h-10 w-40 rounded border border-grid-line bg-terminal-bg" />
        <div className="h-10 w-32 rounded border border-grid-line bg-terminal-bg" />
      </div>

      {/* Payment table */}
      <div className="rounded border border-grid-line bg-terminal-bg overflow-hidden">
        {/* Table header */}
        <div className="flex gap-4 border-b border-grid-line px-4 py-3">
          {[100, 120, 80, 140, 90, 70].map((w, i) => (
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
            {[100, 120, 80, 140, 90, 70].map((w, j) => (
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
