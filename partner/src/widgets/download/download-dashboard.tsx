'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';
import { useVisualTier } from '@/shared/hooks/use-visual-tier';
import { ResponsiveSplitShell } from '@/shared/ui/layout/responsive-split-shell';
import { OSSelector } from './os-selector';
import { TerminalVerifier } from './terminal-verifier';
import { ChangelogAccordion } from './changelog-accordion';

const DownloadPayload3D = dynamic(
  () => import('@/3d/scenes/DownloadPayload3D').then((mod) => mod.DownloadPayload3D),
  {
    ssr: false,
    loading: () => null,
  },
);

export type OSPlatform = 'none' | 'windows' | 'macos' | 'linux' | 'ios' | 'android';

const DOWNLOAD_VISUAL_STYLES: Record<
  OSPlatform,
  {
    glowClassName: string;
    accentBorderClassName: string;
    accentTextClassName: string;
  }
> = {
  none: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.16),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.08)_0%,rgba(0,0,0,0.88)_100%)]',
    accentBorderClassName: 'border-white/20',
    accentTextClassName: 'text-white/75',
  },
  windows: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.2),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.08)_0%,rgba(0,10,12,0.9)_100%)]',
    accentBorderClassName: 'border-neon-cyan/30',
    accentTextClassName: 'text-neon-cyan/80',
  },
  macos: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.18),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.08)_0%,rgba(10,10,10,0.9)_100%)]',
    accentBorderClassName: 'border-white/20',
    accentTextClassName: 'text-white/80',
  },
  linux: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(255,184,0,0.22),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.08)_0%,rgba(16,10,0,0.9)_100%)]',
    accentBorderClassName: 'border-warning/30',
    accentTextClassName: 'text-warning/80',
  },
  ios: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(200,200,200,0.18),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.08)_0%,rgba(8,8,10,0.9)_100%)]',
    accentBorderClassName: 'border-white/20',
    accentTextClassName: 'text-white/80',
  },
  android: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(0,255,136,0.2),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.08)_0%,rgba(0,14,8,0.9)_100%)]',
    accentBorderClassName: 'border-matrix-green/30',
    accentTextClassName: 'text-matrix-green/80',
  },
};

function DownloadVisualFallback({
  selectedOS,
  visualTier,
}: {
  selectedOS: OSPlatform;
  visualTier: 'minimal' | 'reduced' | 'full';
}) {
  const style = DOWNLOAD_VISUAL_STYLES[selectedOS];
  const visualLabel = selectedOS === 'none' ? 'PAYLOAD.QUEUE' : `${selectedOS.toUpperCase()}.SIGNED`;

  return (
    <div aria-hidden="true" data-visual-tier={visualTier} className="absolute inset-0 overflow-hidden">
      <div className={`absolute inset-0 ${style.glowClassName}`} />
      <div className="absolute inset-6 rounded-[2rem] border border-white/10 bg-[linear-gradient(160deg,rgba(255,255,255,0.04),rgba(0,0,0,0.84))] backdrop-blur-xl" />
      <div className={`absolute left-1/2 top-1/2 h-52 w-52 -translate-x-1/2 -translate-y-1/2 rounded-full border ${style.accentBorderClassName}`} />
      <div className={`absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed ${style.accentBorderClassName} opacity-60`} />
      <div className="absolute left-1/2 top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/80 shadow-[0_0_25px_rgba(255,255,255,0.25)]" />
      {visualTier === 'reduced' ? (
        <div className="absolute inset-x-8 bottom-8 flex flex-wrap items-center gap-3 font-mono text-[11px] tracking-[0.28em]">
          <span className={`rounded-full border px-4 py-2 ${style.accentBorderClassName} ${style.accentTextClassName}`}>
            {visualLabel}
          </span>
          <span className="rounded-full border border-white/10 px-4 py-2 text-white/60">
            CHECKSUM.CACHED
          </span>
        </div>
      ) : null}
    </div>
  );
}

export function DownloadDashboard() {
  const t = useTranslations('Download');
  const [selectedOS, setSelectedOS] = useState<OSPlatform>('none');
  const { tier: visualTier } = useVisualTier();
  const { isReady: isSceneReady } = useEnhancementReady({
    minimumTier: 'full',
    defer: 'idle',
  });
  const showScene = visualTier === 'full' && isSceneReady;

  const header = (
    <header className="space-y-2">
      <p className="font-mono text-xs uppercase tracking-widest text-neon-cyan">
        {t('subtitle')}
      </p>
      <h1 className="font-display text-4xl font-black uppercase tracking-widest text-white shadow-black drop-shadow-lg md:text-6xl">
        {t('title')}
      </h1>
    </header>
  );

  const content = (
    <div className="grid grid-cols-1 gap-6 pb-12 lg:grid-cols-12 lg:gap-8 lg:pb-24">
      <div className="flex min-w-0 flex-col gap-6 lg:col-span-5">
        <OSSelector selectedOS={selectedOS} onSelect={setSelectedOS} />
        <TerminalVerifier selectedOS={selectedOS} />
      </div>

      <div className="flex min-w-0 flex-col lg:col-span-7">
        <ChangelogAccordion selectedOS={selectedOS} />
      </div>
    </div>
  );

  const visual = (
    <div data-visual-tier={visualTier} className="absolute inset-0">
      {showScene ? (
        <DownloadPayload3D selectedOS={selectedOS} />
      ) : (
        <DownloadVisualFallback selectedOS={selectedOS} visualTier={visualTier === 'full' ? 'reduced' : visualTier} />
      )}

      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/90 via-transparent to-black/90" />
      <div className="pointer-events-none absolute inset-y-0 left-0 hidden w-1/2 bg-gradient-to-r from-black via-black/80 to-transparent md:block" />
    </div>
  );

  return (
    <ResponsiveSplitShell
      className="min-h-[calc(100dvh-4rem)] bg-black"
      containerClassName="max-w-7xl"
      contentStackClassName="gap-8 md:gap-10"
      header={header}
      content={content}
      visual={visual}
      visualMode="background"
      visualPaneClassName="pointer-events-none rounded-[1.75rem] border border-white/5 bg-black/70 lg:rounded-none lg:border-0"
    />
  );
}
