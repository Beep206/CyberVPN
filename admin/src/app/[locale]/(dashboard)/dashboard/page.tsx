import { Suspense } from 'react';
import { getTranslations } from 'next-intl/server';
import { CommandCenterPanels } from './components/CommandCenterPanels';
import { DashboardGlobe } from './components/DashboardGlobe';
import { DashboardStats } from './components/DashboardStats';
import { ServerGrid } from './components/ServerGrid';

export default async function Dashboard({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Dashboard' });

  return (
    <section className="relative overflow-hidden rounded-[1.75rem] border border-grid-line/20 bg-terminal-bg/85 px-4 py-5 text-foreground shadow-[0_0_40px_rgba(0,255,255,0.04)] md:px-8 md:py-8">
      <DashboardGlobe />

      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(0,255,136,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,136,0.03)_1px,transparent_1px)] bg-[size:40px_40px]" />
      <div className="pointer-events-none absolute left-1/4 top-0 h-72 w-72 rounded-full bg-neon-cyan/20 blur-[100px] md:h-96 md:w-96" />
      <div className="pointer-events-none absolute bottom-0 right-1/4 h-72 w-72 rounded-full bg-neon-purple/20 blur-[100px] md:h-96 md:w-96" />

      <div className="relative z-10 mx-auto max-w-7xl space-y-6 md:space-y-8">
        <header className="mb-8 flex flex-col gap-4 rounded-2xl border border-grid-line/30 bg-terminal-surface/30 p-4 shadow-[0_0_30px_rgba(0,255,255,0.05)] backdrop-blur md:mb-12 md:flex-row md:items-center md:justify-between md:p-6">
          <div className="flex w-full items-start gap-4 md:w-auto md:items-center">
            <div className="hidden h-12 w-12 items-center justify-center rounded-lg border border-neon-cyan/30 bg-neon-cyan/10 md:flex">
              <span className="font-cyber text-2xl text-neon-cyan">ADM</span>
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-mono uppercase tracking-[0.26em] text-neon-cyan/80">
                {t('eyebrow')}
              </p>
              <h1 className="break-words text-2xl font-display tracking-wider text-white drop-shadow-glow md:text-3xl">
                {t('title')}
              </h1>
              <p className="mt-2 max-w-3xl text-sm font-mono leading-6 text-muted-foreground md:text-base">
                {t('subtitle')}
              </p>
              <div className="mt-1 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-matrix-green animate-pulse" />
                <p className="font-mono text-xs text-muted-foreground md:text-sm">
                  {t('statusLabel')}{' '}
                  <span className="font-bold text-matrix-green">
                    {t('statusValue')}
                  </span>
                </p>
              </div>
            </div>
          </div>

          <div className="hidden border-l border-white/10 pl-4 text-right font-cyber text-xs text-neon-pink opacity-80 md:block">
            <div className="mb-1">{t('connectionStatus')}</div>
            <div>{t('encryptionStatus')}</div>
          </div>
        </header>

        <div className="grid gap-8">
          <Suspense
            fallback={
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
                {[...Array(4)].map((_, index) => (
                  <div
                    key={index}
                    className="cyber-card h-32 rounded-xl p-6 animate-pulse"
                  />
                ))}
              </div>
            }
          >
            <DashboardStats />
          </Suspense>

          <Suspense
            fallback={
              <div className="grid gap-6 xl:grid-cols-12">
                <div className="h-72 rounded-2xl border border-grid-line/20 bg-terminal-surface/30 animate-pulse xl:col-span-5" />
                <div className="h-72 rounded-2xl border border-grid-line/20 bg-terminal-surface/30 animate-pulse xl:col-span-7" />
                <div className="h-64 rounded-2xl border border-grid-line/20 bg-terminal-surface/30 animate-pulse xl:col-span-6" />
                <div className="h-64 rounded-2xl border border-grid-line/20 bg-terminal-surface/30 animate-pulse xl:col-span-6" />
                <div className="h-64 rounded-2xl border border-grid-line/20 bg-terminal-surface/30 animate-pulse xl:col-span-12" />
              </div>
            }
          >
            <CommandCenterPanels />
          </Suspense>

          <div className="space-y-4">
            <div className="mb-6 flex items-center gap-2 border-b border-neon-purple/30 pb-2">
              <div className="h-6 w-1 bg-neon-purple" />
              <div>
                <h2 className="text-xl font-display tracking-wide text-neon-purple">
                  {t('serverMatrix')}
                </h2>
                <p className="mt-1 text-sm font-mono text-muted-foreground">
                  {t('serverMatrixDescription')}
                </p>
              </div>
            </div>
            <Suspense
              fallback={
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
                  {[...Array(4)].map((_, index) => (
                    <div
                      key={index}
                      className="cyber-card h-40 rounded-xl p-6 animate-pulse"
                    />
                  ))}
                </div>
              }
            >
              <ServerGrid />
            </Suspense>
          </div>
        </div>
      </div>
    </section>
  );
}
