import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface InfrastructureMetric {
  label: string;
  value: string;
  hint?: string;
  tone?: 'neutral' | 'success' | 'info' | 'warning' | 'danger';
}

interface InfrastructurePageShellProps {
  eyebrow: string;
  title: string;
  description: string;
  icon: LucideIcon;
  actions?: ReactNode;
  metrics?: readonly InfrastructureMetric[];
  children: ReactNode;
}

const metricToneClasses: Record<
  NonNullable<InfrastructureMetric['tone']>,
  string
> = {
  neutral: 'text-white',
  success: 'text-matrix-green',
  info: 'text-neon-cyan',
  warning: 'text-amber-300',
  danger: 'text-neon-pink',
};

export function InfrastructurePageShell({
  eyebrow,
  title,
  description,
  icon: Icon,
  actions,
  metrics = [],
  children,
}: InfrastructurePageShellProps) {
  return (
    <section className="space-y-6">
      <header className="rounded-[1.75rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_40px_rgba(0,255,255,0.04)] md:p-7">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan shadow-[0_0_18px_rgba(0,255,255,0.18)]">
              <Icon className="h-5 w-5" />
            </div>

            <div className="space-y-2">
              <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
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
                    metricToneClasses[metric.tone ?? 'neutral'],
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
