import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SupportMetric {
  hint?: string;
  label: string;
  tone?: 'neutral' | 'success' | 'info' | 'warning' | 'danger';
  value: string;
}

interface SupportPageShellProps {
  actions?: ReactNode;
  children: ReactNode;
  description: string;
  eyebrow: string;
  icon: LucideIcon;
  metrics?: readonly SupportMetric[];
  title: string;
}

const METRIC_TONE_CLASSES: Record<
  NonNullable<SupportMetric['tone']>,
  string
> = {
  neutral: 'text-white',
  success: 'text-matrix-green',
  info: 'text-neon-cyan',
  warning: 'text-amber-300',
  danger: 'text-neon-pink',
};

export function SupportPageShell({
  actions,
  children,
  description,
  eyebrow,
  icon: Icon,
  metrics = [],
  title,
}: SupportPageShellProps) {
  return (
    <section className="space-y-6">
      <header className="rounded-[1.75rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_40px_rgba(0,255,255,0.04)] md:p-7">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-amber-300/30 bg-amber-300/10 text-amber-300 shadow-[0_0_18px_rgba(251,191,36,0.14)]">
              <Icon className="h-5 w-5" />
            </div>

            <div className="space-y-2">
              <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-amber-300/80">
                {eyebrow}
              </p>
              <h1 className="text-2xl font-display tracking-[0.18em] text-white md:text-3xl">
                {title}
              </h1>
              <p className="max-w-3xl text-sm font-mono leading-6 text-muted-foreground md:text-base">
                {description}
              </p>
            </div>
          </div>

          {actions ? (
            <div className="flex shrink-0 flex-wrap items-center gap-3">
              {actions}
            </div>
          ) : null}
        </div>

        {metrics.length > 0 ? (
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {metrics.map((metric) => (
              <article
                key={metric.label}
                className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4 backdrop-blur"
              >
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-muted-foreground">
                  {metric.label}
                </p>
                <p
                  className={cn(
                    'mt-2 text-2xl font-display tracking-[0.12em]',
                    METRIC_TONE_CLASSES[metric.tone ?? 'neutral'],
                  )}
                >
                  {metric.value}
                </p>
                {metric.hint ? (
                  <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
                    {metric.hint}
                  </p>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}
      </header>

      {children}
    </section>
  );
}
