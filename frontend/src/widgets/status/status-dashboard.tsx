'use client';

import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';
import { useVisualTier } from '@/shared/hooks/use-visual-tier';
import { ResponsiveSplitShell } from '@/shared/ui/layout/responsive-split-shell';
import type { UptimeDay } from './uptime-history';
import { MetricsHUD } from './metrics-hud';
import { UptimeMatrix } from './uptime-matrix';
import { IncidentLog } from './incident-log';

const NetworkCore3D = dynamic(
  () => import('@/3d/scenes/StatusNetworkCore3D').then((mod) => mod.NetworkCore3D),
  {
    ssr: false,
    loading: () => null,
  },
);

function StatusVisualFallback({ visualTier }: { visualTier: 'minimal' | 'reduced' | 'full' }) {
  return (
    <div aria-hidden="true" data-visual-tier={visualTier} className="absolute inset-0 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,255,136,0.18),transparent_44%),linear-gradient(180deg,rgba(0,0,0,0.05)_0%,rgba(0,0,0,0.88)_100%)]" />
      <div className="absolute inset-0 opacity-35 [background-image:linear-gradient(rgba(0,255,255,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,255,0.08)_1px,transparent_1px)] [background-size:3rem_3rem]" />
      <div className="absolute left-1/2 top-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 rounded-full border border-matrix-green/30 shadow-[0_0_40px_rgba(0,255,136,0.08)]" />
      <div className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full border border-neon-cyan/15" />
      {visualTier === 'reduced' ? (
        <div className="absolute inset-x-8 bottom-8 flex flex-wrap items-center gap-3 font-mono text-[11px] tracking-[0.26em]">
          <span className="rounded-full border border-matrix-green/30 px-4 py-2 text-matrix-green/80">
            CORE.NOMINAL
          </span>
          <span className="rounded-full border border-white/10 px-4 py-2 text-white/60">
            PASSIVE TELEMETRY
          </span>
        </div>
      ) : null}
    </div>
  );
}

export function StatusDashboard({ historyData }: { historyData: UptimeDay[] }) {
  const t = useTranslations('Status');
  const { tier: visualTier } = useVisualTier();
  const { isReady: isSceneReady } = useEnhancementReady({
    minimumTier: 'full',
    defer: 'idle',
  });
  const showScene = visualTier === 'full' && isSceneReady;

  const header = (
    <header className="space-y-2">
      <h1 className="font-display text-3xl font-black uppercase tracking-widest text-white md:text-5xl">
        {t('title')}
      </h1>
      <p className="font-mono text-sm uppercase tracking-widest text-neon-cyan">
        {t('subtitle')}
      </p>
    </header>
  );

  const content = (
    <div className="grid grid-cols-1 gap-6 pb-12 lg:grid-cols-12 lg:gap-8 lg:pb-20">
      <div className="flex min-w-0 flex-col gap-6 lg:col-span-4">
        <MetricsHUD />
        <IncidentLog />
      </div>

      <div className="flex min-w-0 flex-col gap-6 lg:col-span-8 lg:justify-end lg:pb-8">
        <UptimeMatrix data={historyData} />
      </div>
    </div>
  );

  const visual = (
    <div data-visual-tier={visualTier} className="absolute inset-0">
      {showScene ? <NetworkCore3D /> : <StatusVisualFallback visualTier={visualTier === 'full' ? 'reduced' : visualTier} />}

      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/80 via-transparent to-black/80" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-black/80 via-transparent to-black/80 md:hidden" />
      <div className="pointer-events-none absolute inset-y-0 left-0 hidden w-1/3 bg-gradient-to-r from-black via-black/50 to-transparent md:block" />
      <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-1/3 bg-gradient-to-l from-black via-black/50 to-transparent md:block" />
    </div>
  );

  return (
    <ResponsiveSplitShell
      className="min-h-[calc(100dvh-4rem)] bg-black"
      containerClassName="max-w-[1680px]"
      contentStackClassName="gap-8"
      header={header}
      content={content}
      visual={visual}
      visualMode="background"
      visualPaneClassName="pointer-events-none rounded-[1.75rem] border border-white/5 bg-black/70 lg:rounded-none lg:border-0"
    />
  );
}
