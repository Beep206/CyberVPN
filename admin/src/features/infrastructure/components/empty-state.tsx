export function InfrastructureEmptyState({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-10 text-center text-sm font-mono text-muted-foreground">
      {label}
    </div>
  );
}
