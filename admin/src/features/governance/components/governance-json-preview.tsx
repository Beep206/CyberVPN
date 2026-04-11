import { stringifyJson } from '@/features/governance/lib/formatting';

export function GovernanceJsonPreview({
  value,
  maxHeightClassName = 'max-h-[28rem]',
}: {
  value: unknown;
  maxHeightClassName?: string;
}) {
  return (
    <pre
      className={`overflow-auto rounded-2xl border border-grid-line/20 bg-terminal-bg/65 p-4 text-xs font-mono leading-6 text-muted-foreground ${maxHeightClassName}`}
    >
      {stringifyJson(value)}
    </pre>
  );
}
