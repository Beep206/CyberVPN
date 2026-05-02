import { Suspense } from 'react';
import { getTranslations } from 'next-intl/server';
import { DashboardGlobe } from './components/DashboardGlobe';
import { CustomerCabinetDashboard } from '@/widgets/customer-cabinet/customer-cabinet-dashboard';

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
              <span className="font-cyber text-2xl text-neon-cyan">CV</span>
            </div>
            <div className="min-w-0">
              <p className="mb-2 font-mono text-xs uppercase tracking-[0.32em] text-neon-cyan">
                {t('cabinet.eyebrow')}
              </p>
              <h1 className="break-words text-2xl font-display tracking-wider text-white drop-shadow-glow md:text-3xl">
                {t('cabinet.title')}
              </h1>
              <div className="mt-2 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-matrix-green animate-pulse" />
                <p className="font-mono text-xs text-muted-foreground md:text-sm">
                  {t('cabinet.statusLabel')}{' '}
                  <span className="font-bold text-matrix-green">
                    {t('cabinet.statusValue')}
                  </span>
                </p>
              </div>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground md:text-base">
                {t('cabinet.subtitle')}
              </p>
            </div>
          </div>

          <div className="hidden border-l border-white/10 pl-4 text-right font-cyber text-xs text-neon-pink opacity-80 md:block">
            <div className="mb-1">{t('cabinet.connectionStatus')}</div>
            <div>{t('cabinet.encryptionStatus')}</div>
          </div>
        </header>

        <Suspense
          fallback={
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
              {[...Array(8)].map((_, index) => (
                <div
                  key={index}
                  className="cyber-card h-36 rounded-xl p-6 animate-pulse"
                />
              ))}
            </div>
          }
        >
          <CustomerCabinetDashboard />
        </Suspense>
      </div>
    </section>
  );
}
