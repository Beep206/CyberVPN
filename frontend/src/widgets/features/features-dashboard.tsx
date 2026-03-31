'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';
import { useVisualTier } from '@/shared/hooks/use-visual-tier';
import { ResponsiveSplitShell } from '@/shared/ui/layout/responsive-split-shell';
import { FeatureModules } from './feature-modules';
import { TechSpecsTerminal } from './tech-specs-terminal';
import { SecondaryGrid } from './secondary-grid';

const FeaturesScene3D = dynamic(
  () => import('@/3d/scenes/FeaturesScene3D').then((mod) => mod.FeaturesScene3D),
  {
    ssr: false,
    loading: () => null,
  },
);

export type FeatureId = 'quantum' | 'multihop' | 'obfuscation' | 'killswitch';

const FEATURE_VISUAL_STYLES: Record<
  FeatureId,
  {
    glowClassName: string;
    accentBorderClassName: string;
    accentTextClassName: string;
    label: string;
  }
> = {
  quantum: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.24),transparent_56%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(0,9,14,0.82)_100%)]',
    accentBorderClassName: 'border-neon-cyan/30',
    accentTextClassName: 'text-neon-cyan/80',
    label: 'QUANTUM.SHIELD',
  },
  multihop: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(0,255,136,0.24),transparent_56%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(0,14,8,0.82)_100%)]',
    accentBorderClassName: 'border-matrix-green/30',
    accentTextClassName: 'text-matrix-green/80',
    label: 'MULTIHOP.MESH',
  },
  obfuscation: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(255,0,255,0.2),transparent_56%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(12,0,14,0.84)_100%)]',
    accentBorderClassName: 'border-neon-purple/30',
    accentTextClassName: 'text-neon-purple/80',
    label: 'MASKING.LAYER',
  },
  killswitch: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(255,51,0,0.22),transparent_56%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(18,4,0,0.84)_100%)]',
    accentBorderClassName: 'border-warning/30',
    accentTextClassName: 'text-warning/80',
    label: 'FAILSAFE.CORE',
  },
};

function FeatureVisualFallback({
  activeFeature,
  visualTier,
}: {
  activeFeature: FeatureId;
  visualTier: 'minimal' | 'reduced' | 'full';
}) {
  const style = FEATURE_VISUAL_STYLES[activeFeature];

  return (
    <div aria-hidden="true" data-visual-tier={visualTier} className="absolute inset-0 overflow-hidden">
      <div className={`absolute inset-0 ${style.glowClassName}`} />
      <div className="absolute inset-6 rounded-[2rem] border border-white/10 bg-[linear-gradient(160deg,rgba(255,255,255,0.05),rgba(0,0,0,0.86))] backdrop-blur-xl" />
      <div className={`absolute inset-10 rounded-[1.75rem] border ${style.accentBorderClassName}`} />
      <div className="absolute inset-x-12 top-12 grid grid-cols-3 gap-3 opacity-70">
        <div className="h-20 rounded-2xl border border-white/10 bg-black/35" />
        <div className="h-16 rounded-2xl border border-white/10 bg-white/[0.03]" />
        <div className="h-24 rounded-2xl border border-white/10 bg-black/35" />
      </div>
      {visualTier === 'reduced' ? (
        <div className="absolute inset-x-14 bottom-16 grid gap-3">
          <div className={`inline-flex w-fit items-center rounded-full border px-4 py-2 text-[11px] font-mono tracking-[0.3em] ${style.accentBorderClassName} ${style.accentTextClassName}`}>
            {style.label}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-2xl border border-white/10 bg-black/35 px-4 py-3 font-mono text-[11px] tracking-[0.24em] text-white/65">
              EDGE ROUTING
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/35 px-4 py-3 font-mono text-[11px] tracking-[0.24em] text-white/65">
              STATIC PREVIEW
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function FeaturesDashboard() {
  const t = useTranslations('Features');
  const [activeFeature, setActiveFeature] = useState<FeatureId>('quantum');
  const { tier: visualTier, isFull } = useVisualTier();
  const { isReady: isSceneReady } = useEnhancementReady({
    minimumTier: 'full',
    defer: 'idle',
  });
  const showScene = visualTier === 'full' && isSceneReady;

  const header = (
    <motion.div
      initial={isFull ? { opacity: 0, y: 20 } : undefined}
      animate={isFull ? { opacity: 1, y: 0 } : undefined}
      transition={isFull ? { duration: 0.8 } : undefined}
    >
      <h1 className="font-display text-4xl font-black uppercase tracking-tighter text-white md:text-5xl lg:text-6xl">
        {t('title')}
      </h1>
      <p className="mt-4 max-w-md font-mono text-muted-foreground">
        {t('description')}
      </p>
    </motion.div>
  );

  const content = (
    <div className="flex min-w-0 flex-col gap-8">
      <FeatureModules activeFeature={activeFeature} setActiveFeature={setActiveFeature} />
      <TechSpecsTerminal activeFeature={activeFeature} />

      <div className="mt-4 pb-4 md:mt-10 md:pb-8">
        <SecondaryGrid />
      </div>
    </div>
  );

  const visual = (
    <div
      data-visual-tier={visualTier}
      className="relative h-full min-h-[20rem] overflow-hidden rounded-[1.75rem] border border-grid-line/30 bg-terminal-bg/60 shadow-[0_0_40px_rgba(0,255,255,0.08)] lg:min-h-[calc(100dvh-4rem)] lg:rounded-none lg:border-x-0 lg:border-y-0 lg:border-l"
    >
      <div className="pointer-events-none absolute inset-0 z-10 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.8)_100%)]" />

      <div className="absolute inset-0 h-full w-full overflow-hidden opacity-80 mix-blend-screen">
        {showScene ? (
          <FeaturesScene3D activeFeature={activeFeature} />
        ) : (
          <FeatureVisualFallback activeFeature={activeFeature} visualTier={visualTier === 'full' ? 'reduced' : visualTier} />
        )}
      </div>

      <div className="pointer-events-none absolute right-6 top-6 z-20 flex flex-col items-end font-mono text-xs text-matrix-green/70">
        <span>{showScene ? 'SYS.CORE.ENGAGED' : 'SYS.CORE.DEFERRED'}</span>
        <span>OP.MODE: {activeFeature.toUpperCase()}</span>
        <span className={showScene ? 'animate-pulse' : ''}>
          {showScene ? 'RENDERING...' : visualTier === 'minimal' ? 'POWER SAVE' : 'STATIC PREVIEW'}
        </span>
      </div>
    </div>
  );

  return (
    <ResponsiveSplitShell
      className="min-h-[calc(100dvh-4rem)] bg-black"
      containerClassName="max-w-[1680px]"
      contentPaneClassName="lg:col-span-5"
      contentStackClassName="gap-10 md:gap-12"
      pinVisualOnDesktop
      visualPaneClassName="lg:col-span-7"
      header={header}
      content={content}
      visual={visual}
    />
  );
}
