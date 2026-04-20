import { Terminal } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import { LazyMount } from '@/shared/ui/lazy-mount';
import { Reveal } from '@/shared/ui/reveal';
import { TiltCard } from '@/shared/ui/tilt-card';
import { QuickStartCopyButton } from '@/widgets/quick-start-copy-button';
import { QuickStartScene } from '@/widgets/quick-start-scene';

export async function QuickStart() {
  const t = await getTranslations('Landing.quick_start');

  return (
    <section className="relative py-32 bg-terminal-bg border-t border-grid-line/20 overflow-hidden">
      <LazyMount
        className="absolute inset-0 z-0 pointer-events-none"
        defer="idle"
        minimumTier="full"
        placeholder={<div className="absolute inset-0 z-0" />}
      >
        <QuickStartScene />
      </LazyMount>

      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 bg-grid-white/[0.015] bg-[size:50px_50px]" />
        <div className="absolute inset-0 scanline opacity-30" />
      </div>

      <div className="container mx-auto px-4 relative z-10 max-w-5xl flex flex-col items-center">
        <Reveal className="text-center mb-16">
          <div className="inline-block mb-6 px-4 py-1.5 rounded-full border border-matrix-green/30 bg-matrix-green/10 text-matrix-green text-sm font-mono tracking-widest uppercase">
            {t('badge')}
          </div>
          <h2 className="text-4xl md:text-6xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-cyan via-matrix-green to-neon-cyan mb-6">
            {t('title')}
          </h2>
        </Reveal>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
          <Reveal className="h-full">
            <TiltCard className="flex flex-col items-center gap-6 p-8 h-full rounded-2xl group w-full text-center hover:border-neon-cyan/50 transition-colors">
              <div className="w-20 h-20 rounded-2xl bg-terminal-bg border border-neon-cyan/40 flex items-center justify-center text-neon-cyan font-display font-bold text-3xl shadow-[0_0_15px_rgba(0,255,255,0.2)] group-hover:shadow-[0_0_25px_rgba(0,255,255,0.5)] transition-shadow">
                1
              </div>
              <div className="flex flex-col items-center gap-3 w-full">
                <p className="text-foreground font-mono text-lg">{t('step1')}</p>
                <QuickStartCopyButton value="@CyberVPN_Bot" />
              </div>
            </TiltCard>
          </Reveal>

          <Reveal delay={0.15} className="h-full">
            <TiltCard className="flex flex-col items-center gap-6 p-8 h-full rounded-2xl group w-full text-center hover:border-neon-purple/50 transition-colors">
              <div className="w-20 h-20 rounded-2xl bg-terminal-bg border border-neon-purple/40 flex items-center justify-center text-neon-purple font-display font-bold text-3xl shadow-[0_0_15px_rgba(157,0,255,0.2)] group-hover:shadow-[0_0_25px_rgba(157,0,255,0.5)] transition-shadow">
                2
              </div>
              <div className="flex flex-col items-center gap-3 w-full justify-center flex-1">
                <p className="text-foreground font-mono text-lg">{t('step2')}</p>
              </div>
            </TiltCard>
          </Reveal>

          <Reveal delay={0.3} className="h-full">
            <TiltCard className="flex flex-col items-center gap-6 p-8 h-full rounded-2xl group w-full text-center hover:border-matrix-green/50 transition-colors">
              <div className="w-20 h-20 rounded-2xl bg-terminal-bg border border-matrix-green/40 flex items-center justify-center text-matrix-green font-display font-bold text-3xl shadow-[0_0_15px_rgba(0,255,136,0.2)] group-hover:shadow-[0_0_25px_rgba(0,255,136,0.5)] transition-shadow">
                3
              </div>
              <div className="flex flex-col items-center gap-3 w-full justify-center flex-1">
                <p className="text-foreground font-mono text-lg">{t('step3')}</p>
              </div>
            </TiltCard>
          </Reveal>
        </div>

        <Reveal delay={0.45} className="mt-20 w-full max-w-3xl overflow-hidden rounded-xl border border-grid-line/50 bg-terminal-bg/80 backdrop-blur-xl shadow-2xl relative">
          <div className="flex items-center px-4 py-3 border-b border-grid-line/50 bg-black/40">
            <div className="flex gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <div className="w-3 h-3 rounded-full bg-green-500/80" />
            </div>
            <div className="mx-auto font-mono text-xs text-muted-foreground uppercase flex items-center gap-2">
              <Terminal size={12} />
              {t('terminalTitle')}
            </div>
          </div>

          <div className="p-6 font-mono text-sm md:text-base leading-relaxed relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-matrix-green/5 to-transparent pointer-events-none" />
            <div className="text-muted-foreground mb-2">{t('terminalComment')}</div>
            <div className="flex items-center text-matrix-green mb-1">
              <span className="opacity-50 select-none mr-3">sys@admin:~$</span>
              <span className="break-all">curl -sL https://get.cybervpn.com | bash -s -- --protocol=vless-reality</span>
            </div>
            <div className="text-neon-cyan mt-4 animate-pulse">
              {t('terminalStatus')}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
