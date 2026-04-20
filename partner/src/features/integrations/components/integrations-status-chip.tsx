import { cn } from '@/lib/utils';

const TONE_STYLES = {
  neutral: 'border-grid-line/30 bg-terminal-bg/50 text-muted-foreground',
  success: 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green',
  info: 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan',
  warning: 'border-amber-300/30 bg-amber-300/10 text-amber-200',
  danger: 'border-neon-pink/30 bg-neon-pink/10 text-neon-pink',
} as const;

export function IntegrationsStatusChip({
  label,
  tone = 'neutral',
}: {
  label: string;
  tone?: keyof typeof TONE_STYLES;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em]',
        TONE_STYLES[tone],
      )}
    >
      {label}
    </span>
  );
}
