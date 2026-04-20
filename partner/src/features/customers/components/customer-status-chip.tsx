import { cn } from '@/lib/utils';

interface CustomerStatusChipProps {
  label: string;
  tone?: 'neutral' | 'success' | 'info' | 'warning' | 'danger';
}

const toneClasses: Record<NonNullable<CustomerStatusChipProps['tone']>, string> = {
  neutral: 'border-grid-line/20 bg-terminal-bg/45 text-muted-foreground',
  success: 'border-matrix-green/25 bg-matrix-green/10 text-matrix-green',
  info: 'border-neon-cyan/25 bg-neon-cyan/10 text-neon-cyan',
  warning: 'border-amber-300/25 bg-amber-300/10 text-amber-200',
  danger: 'border-neon-pink/25 bg-neon-pink/10 text-neon-pink',
};

export function CustomerStatusChip({
  label,
  tone = 'neutral',
}: CustomerStatusChipProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em]',
        toneClasses[tone],
      )}
    >
      {label}
    </span>
  );
}
