import { getTranslations } from 'next-intl/server';
import { LazyMount } from '@/shared/ui/lazy-mount';
import { Reveal } from '@/shared/ui/reveal';
import { ScrambleText } from '@/shared/ui/scramble-text';
import { LandingFeaturesGrid } from '@/widgets/landing-features-grid';
import { LandingFeaturesScene } from '@/widgets/landing-features-scene';

interface FeatureConfigItem {
  bgColor: string;
  colSpan: string;
  color: string;
  iconKey: 'backbone' | 'multiplatform' | 'protocols' | 'ram' | 'routing' | 'stealth';
  id: string;
}

const FEATURE_CONFIG: FeatureConfigItem[] = [
  {
    id: 'stealth',
    iconKey: 'stealth',
    color: 'text-neon-cyan',
    bgColor: 'bg-neon-cyan/15 dark:bg-neon-cyan/10',
    colSpan: 'md:col-span-2',
  },
  {
    id: 'backbone',
    iconKey: 'backbone',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-400/15 dark:bg-yellow-400/10',
    colSpan: 'md:col-span-1',
  },
  {
    id: 'ram',
    iconKey: 'ram',
    color: 'text-neon-purple',
    bgColor: 'bg-neon-purple/15 dark:bg-neon-purple/10',
    colSpan: 'md:col-span-1',
  },
  {
    id: 'routing',
    iconKey: 'routing',
    color: 'text-blue-400',
    bgColor: 'bg-blue-400/15 dark:bg-blue-400/10',
    colSpan: 'md:col-span-1',
  },
  {
    id: 'multiplatform',
    iconKey: 'multiplatform',
    color: 'text-matrix-green',
    bgColor: 'bg-matrix-green/15 dark:bg-matrix-green/10',
    colSpan: 'md:col-span-1',
  },
  {
    id: 'protocols',
    iconKey: 'protocols',
    color: 'text-neon-pink',
    bgColor: 'bg-neon-pink/15 dark:bg-neon-pink/10',
    colSpan: 'md:col-span-2',
  },
] as const;

const STATS = [
  { value: '100+', labelKey: 'stats.locations' },
  { value: '10', labelKey: 'stats.bandwidth' },
  { value: '99.9%', labelKey: 'stats.uptime' },
  { value: '0', labelKey: 'stats.logs' },
] as const;

export async function LandingFeatures() {
  const t = await getTranslations('Landing.features');

  return (
    <section className="relative py-32 bg-terminal-bg overflow-hidden">
      <LazyMount
        className="absolute inset-0 z-0 pointer-events-none"
        defer="idle"
        minimumTier="full"
        placeholder={<div className="absolute inset-0 z-0" />}
      >
        <LandingFeaturesScene />
      </LazyMount>

      <div className="absolute inset-0 bg-grid-white/[0.02] bg-[size:30px_30px] z-[1]" />
      <div className="absolute inset-0 bg-gradient-to-b from-terminal-bg via-transparent to-terminal-bg z-[2]" />
      <div className="absolute inset-0 bg-terminal-bg/60 z-[2]" />

      <div className="container px-4 mx-auto relative z-10">
        <Reveal className="text-center mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan text-xs font-mono mb-6 backdrop-blur-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-pulse" />
            {t('badge')}
          </div>

          <h2 className="text-4xl md:text-6xl lg:text-7xl font-display font-bold mb-6">
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-neon-cyan via-neon-purple to-neon-pink">
              {t('sectionTitle')}
            </span>
          </h2>

          <p className="text-muted-foreground font-mono text-lg md:text-xl max-w-2xl mx-auto">
            {t('sectionSubtitle')}
          </p>
        </Reveal>

        <LandingFeaturesGrid
          features={FEATURE_CONFIG.map((feature) => ({
            ...feature,
            title: t(`${feature.id}.title`),
            description: t(`${feature.id}.desc`),
          }))}
        />

        <Reveal delay={0.2} className="relative rounded-2xl border border-grid-line/40 bg-terminal-surface/60 dark:bg-black/40 backdrop-blur-xl p-8 overflow-hidden">
          <div className="absolute -left-20 -top-20 w-40 h-40 bg-neon-cyan/20 rounded-full blur-[80px] pointer-events-none" />
          <div className="absolute -right-20 -bottom-20 w-40 h-40 bg-neon-purple/20 rounded-full blur-[80px] pointer-events-none" />

          <div className="relative z-10 grid grid-cols-2 md:grid-cols-4 gap-8">
            {STATS.map((stat, index) => (
              <Reveal key={stat.labelKey} delay={0.3 + index * 0.1} className="text-center">
                <div className="text-3xl md:text-5xl font-display font-bold text-neon-cyan mb-2">
                  <ScrambleText text={stat.value} />
                </div>
                <div className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
                  {t(stat.labelKey)}
                </div>
              </Reveal>
            ))}
          </div>

          <div className="absolute left-0 right-0 bottom-0 h-px bg-gradient-to-r from-transparent via-neon-cyan to-transparent opacity-70" />
        </Reveal>
      </div>
    </section>
  );
}
