import { cn } from '@/lib/utils';

type SupportChipTone = 'neutral' | 'success' | 'info' | 'warning' | 'danger';

interface SupportStatusChipProps {
  className?: string;
  label: string;
  tone?: SupportChipTone;
}

const TONE_CLASSES: Record<SupportChipTone, string> = {
  neutral: 'border-grid-line/20 bg-terminal-bg/50 text-muted-foreground',
  success: 'border-matrix-green/35 bg-matrix-green/10 text-matrix-green',
  info: 'border-neon-cyan/35 bg-neon-cyan/10 text-neon-cyan',
  warning: 'border-amber-400/35 bg-amber-400/10 text-amber-300',
  danger: 'border-neon-pink/35 bg-neon-pink/10 text-neon-pink',
};

export function SupportStatusChip({
  className,
  label,
  tone = 'neutral',
}: SupportStatusChipProps) {
  return (
    <span
      className={cn(
        'inline-flex rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em]',
        TONE_CLASSES[tone],
        className,
      )}
    >
      {label}
    </span>
  );
}
