interface SecurityEmptyStateProps {
  label: string;
}

export function SecurityEmptyState({ label }: SecurityEmptyStateProps) {
  return (
    <div className="rounded-2xl border border-dashed border-grid-line/25 bg-terminal-bg/30 p-8 text-center">
      <p className="text-sm font-mono uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
    </div>
  );
}
