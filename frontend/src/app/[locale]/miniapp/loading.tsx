export default function MiniAppLoading() {
  return (
    <div className="animate-pulse space-y-4 p-4" aria-label="Loading">
      <div className="h-32 rounded-sm bg-terminal-surface/50 border border-grid-line" />
      <div className="flex gap-3">
        <div className="h-10 flex-1 rounded-xs bg-neon-cyan/10" />
        <div className="h-10 flex-1 rounded-xs bg-neon-cyan/10" />
      </div>
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="flex items-center gap-3 rounded-sm border border-grid-line/50 p-3">
          <div className="h-8 w-8 rounded-full bg-foreground/5" />
          <div className="flex-1 space-y-1">
            <div className="h-3 w-24 rounded-xs bg-foreground/5" />
            <div className="h-2 w-16 rounded-xs bg-foreground/5" />
          </div>
          <div className="h-4 w-12 rounded-xs bg-foreground/5" />
        </div>
      ))}
    </div>
  );
}
