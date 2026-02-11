export default function AuthLoading() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]" aria-label="Loading">
      <div className="w-full max-w-md animate-pulse space-y-6 p-6">
        <div className="flex justify-center">
          <div className="h-12 w-12 rounded-lg bg-neon-cyan/10" />
        </div>
        <div className="space-y-2 text-center">
          <div className="mx-auto h-6 w-48 rounded-xs bg-neon-cyan/10" />
          <div className="mx-auto h-3 w-64 rounded-xs bg-foreground/5" />
        </div>
        {Array.from({ length: 3 }, (_, i) => (
          <div key={i} className="space-y-1">
            <div className="h-3 w-16 rounded-xs bg-foreground/5" />
            <div className="h-10 rounded-sm border border-grid-line bg-terminal-surface/50" />
          </div>
        ))}
        <div className="h-10 rounded-sm bg-neon-cyan/10" />
      </div>
    </div>
  );
}
