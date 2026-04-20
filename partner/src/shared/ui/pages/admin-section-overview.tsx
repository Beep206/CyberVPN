import type { LucideIcon } from 'lucide-react';
import { ArrowUpRight, Layers3 } from 'lucide-react';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';

type SectionReadinessTone = 'strong' | 'partial' | 'blocked';

interface AdminSectionOverviewProps {
  icon: LucideIcon;
  title: string;
  description: string;
  currentState: string;
  backendCoverage: string;
  nextFocus: string;
  availableNowLabel: string;
  nextModulesLabel: string;
  currentStateLabel: string;
  backendCoverageLabel: string;
  nextFocusLabel: string;
  returnToDashboardLabel: string;
  availableNow: readonly string[];
  nextModules: readonly string[];
  readinessTone: SectionReadinessTone;
}

const toneClasses: Record<SectionReadinessTone, string> = {
  strong: 'border-matrix-green/35 bg-matrix-green/10 text-matrix-green',
  partial: 'border-neon-cyan/35 bg-neon-cyan/10 text-neon-cyan',
  blocked: 'border-neon-pink/35 bg-neon-pink/10 text-neon-pink',
};

export function AdminSectionOverview({
  icon: Icon,
  title,
  description,
  currentState,
  backendCoverage,
  nextFocus,
  availableNowLabel,
  nextModulesLabel,
  currentStateLabel,
  backendCoverageLabel,
  nextFocusLabel,
  returnToDashboardLabel,
  availableNow,
  nextModules,
  readinessTone,
}: AdminSectionOverviewProps) {
  return (
    <section className="relative overflow-hidden rounded-[1.75rem] border border-grid-line/20 bg-terminal-bg/85 px-4 py-5 text-foreground shadow-[0_0_40px_rgba(0,255,255,0.04)] md:px-8 md:py-8">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(0,255,136,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,136,0.03)_1px,transparent_1px)] bg-[size:40px_40px]" />
      <div className="pointer-events-none absolute left-0 top-0 h-64 w-64 rounded-full bg-neon-cyan/10 blur-[100px]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-64 w-64 rounded-full bg-neon-pink/10 blur-[100px]" />

      <div className="relative z-10 mx-auto max-w-7xl space-y-6 md:space-y-8">
        <header className="rounded-2xl border border-grid-line/30 bg-terminal-surface/35 p-5 shadow-[0_0_30px_rgba(0,255,255,0.05)] backdrop-blur md:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex min-w-0 items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan shadow-[0_0_18px_rgba(0,255,255,0.18)]">
                <Icon className="h-5 w-5" />
              </div>

              <div className="min-w-0 space-y-3">
                <h1 className="break-words text-2xl font-display tracking-[0.2em] text-white md:text-3xl">
                  {title}
                </h1>
                <p className="max-w-3xl text-sm font-mono leading-6 text-muted-foreground md:text-base">
                  {description}
                </p>
              </div>
            </div>

            <div className={cn(
              'inline-flex items-center gap-2 self-start rounded-full border px-3 py-2 text-[11px] font-mono uppercase tracking-[0.2em]',
              toneClasses[readinessTone],
            )}>
              <Layers3 className="h-3.5 w-3.5" />
              <span>{backendCoverage}</span>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-full border border-grid-line/30 bg-terminal-bg/70 px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan/40 hover:text-white"
            >
              <span>{returnToDashboardLabel}</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </header>

        <div className="grid gap-4 lg:grid-cols-3">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-5 backdrop-blur">
            <h2 className="text-xs font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
              {currentStateLabel}
            </h2>
            <p className="mt-3 text-sm font-mono leading-6 text-foreground/90">
              {currentState}
            </p>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-5 backdrop-blur">
            <h2 className="text-xs font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
              {backendCoverageLabel}
            </h2>
            <p className="mt-3 text-sm font-mono leading-6 text-foreground/90">
              {backendCoverage}
            </p>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-5 backdrop-blur">
            <h2 className="text-xs font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
              {nextFocusLabel}
            </h2>
            <p className="mt-3 text-sm font-mono leading-6 text-foreground/90">
              {nextFocus}
            </p>
          </article>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-6 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-neon-cyan">
              {availableNowLabel}
            </h2>
            <ul className="mt-4 grid gap-3">
              {availableNow.map((item) => (
                <li
                  key={item}
                  className="rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-foreground/90"
                >
                  {item}
                </li>
              ))}
            </ul>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-6 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-neon-pink">
              {nextModulesLabel}
            </h2>
            <ul className="mt-4 grid gap-3">
              {nextModules.map((item) => (
                <li
                  key={item}
                  className="rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-foreground/90"
                >
                  {item}
                </li>
              ))}
            </ul>
          </article>
        </div>
      </div>
    </section>
  );
}
