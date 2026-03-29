import { Download, Rocket } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import { Button } from '@/components/ui/button';
import { GlobalNetworkWrapper } from '@/widgets/3d-background/global-network-wrapper';
import { Reveal } from '@/shared/ui/reveal';
import { ScrambleText } from '@/shared/ui/scramble-text';
import { StatusBadgeLive } from '@/shared/ui/status-badge-live';

export async function LandingHero() {
  const t = await getTranslations('Landing.hero');
  const protocolBadge = t('protocol_badge').split('|')[0]?.trim().replace('PROTOCOL: ', '') || 'VLESS-REALITY + XHTTP';

  return (
    <section className="relative min-h-[90vh] flex flex-col items-center justify-center overflow-hidden bg-terminal-bg">
      <div className="absolute inset-0 z-0">
        <GlobalNetworkWrapper />
        <div className="absolute inset-0 bg-terminal-bg/80 via-terminal-bg/60 to-transparent bg-gradient-to-b" />
      </div>
      <div className="absolute inset-0 z-0 bg-grid-white/[0.02] bg-[size:50px_50px] pointer-events-none" />
      <div className="absolute inset-0 z-0 scanline opacity-20 pointer-events-none" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-neon-cyan/8 dark:bg-neon-cyan/20 rounded-full blur-[100px] animate-pulse pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-neon-purple/8 dark:bg-neon-purple/20 rounded-full blur-[100px] animate-pulse delay-1000 pointer-events-none" />

      <div className="container relative z-10 flex flex-col items-center text-center px-4">
        <Reveal delay={0.1} className="mb-6 flex justify-center">
          <StatusBadgeLive
            protocol={protocolBadge}
            status="ACTIVE"
            nodeName="CORE: XRAY-CORE"
            className="scale-110"
          />
        </Reveal>

        <Reveal variant="scale">
          <h1 className="text-5xl md:text-8xl font-display font-bold tracking-tighter text-foreground dark:text-transparent dark:bg-clip-text dark:bg-gradient-to-b dark:from-white dark:to-white/50 mb-6 drop-shadow-lg py-4 leading-normal">
            <ScrambleText text={t('title')} /> <br />
            <span className="text-neon-cyan dark:neon-text font-bold">{t('titleHighlight')}</span>
          </h1>
        </Reveal>

        <Reveal delay={0.2}>
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-10 font-mono">
            {t('subtitle')}
          </p>
        </Reveal>

        <Reveal delay={0.4} className="flex flex-col sm:flex-row gap-4 w-full justify-center">
          <Button size="lg" className="bg-neon-cyan hover:bg-neon-cyan/80 text-black font-bold tracking-wide shadow-neon-cyan hover:shadow-neon-cyan/50 transition-all h-12 px-8 text-base group" data-hoverable>
            <Rocket className="mr-2 h-5 w-5 group-hover:-translate-y-1 transition-transform" />
            {t('cta_telegram')}
          </Button>
          <Button variant="outline" size="lg" className="border-neon-purple text-neon-purple hover:bg-neon-purple/10 font-bold tracking-wide h-12 px-8 text-base backdrop-blur-sm" data-hoverable>
            <Download className="mr-2 h-5 w-5" />
            {t('cta_app')}
          </Button>
        </Reveal>
      </div>

      <div className="absolute bottom-0 w-full h-24 bg-gradient-to-t from-terminal-bg to-transparent z-10 pointer-events-none" />
    </section>
  );
}
