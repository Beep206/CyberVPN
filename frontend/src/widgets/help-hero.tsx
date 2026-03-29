import { Search } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import { GlobalNetworkWrapper } from '@/widgets/3d-background/global-network-wrapper';
import { Reveal } from '@/shared/ui/reveal';
import { ScrambleText } from '@/shared/ui/scramble-text';

export async function HelpHero() {
  const t = await getTranslations('HelpCenter');

  return (
    <section className="relative min-h-[60vh] flex flex-col items-center justify-center overflow-hidden bg-terminal-bg">
      <div className="absolute inset-0 z-0">
        <GlobalNetworkWrapper />
        <div className="absolute inset-0 bg-terminal-bg/80 via-terminal-bg/60 to-transparent bg-gradient-to-b" />
      </div>

      <div className="absolute inset-0 z-0 bg-grid-white/[0.02] bg-[size:50px_50px] pointer-events-none" />
      <div className="absolute inset-0 z-0 scanline opacity-20 pointer-events-none" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-neon-cyan/8 dark:bg-neon-cyan/15 rounded-full blur-[100px] animate-pulse pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-neon-purple/8 dark:bg-neon-purple/15 rounded-full blur-[100px] animate-pulse delay-1000 pointer-events-none" />

      <div className="container relative z-10 flex flex-col items-center text-center px-4 mt-16">
        <Reveal variant="scale">
          <h1 className="text-5xl md:text-7xl font-display font-bold tracking-tighter text-foreground dark:text-transparent dark:bg-clip-text dark:bg-gradient-to-b dark:from-white dark:to-white/50 mb-4 drop-shadow-lg">
            <ScrambleText text={t('hero_title')} />
          </h1>
        </Reveal>

        <Reveal delay={0.2}>
          <p className="text-lg text-neon-cyan/80 max-w-2xl mb-12 font-mono tracking-widest">
            {t('hero_subtitle')}
          </p>
        </Reveal>

        <Reveal delay={0.4} className="w-full max-w-2xl relative">
          <div className="absolute -inset-1 bg-gradient-to-r from-neon-cyan via-matrix-green to-neon-purple opacity-30 blur rounded-lg" />
          <div className="relative flex items-center bg-terminal-card border border-terminal-border rounded-lg overflow-hidden focus-within:border-neon-cyan/50 focus-within:shadow-[0_0_15px_rgba(0,255,255,0.2)] transition-all">
            <div className="pl-4 pr-2">
              <Search className="h-5 w-5 text-muted-foreground" />
            </div>
            <input
              type="text"
              placeholder={t('search_placeholder')}
              className="w-full bg-transparent border-none py-4 px-2 text-foreground font-mono focus:outline-none placeholder:text-muted-foreground/50"
            />
            <button className="bg-neon-cyan/10 hover:bg-neon-cyan/20 text-neon-cyan px-6 py-4 font-bold border-l border-terminal-border transition-colors uppercase tracking-wider text-sm whitespace-nowrap">
              {t('search_button')}
            </button>
          </div>
        </Reveal>
      </div>

      <div className="absolute bottom-0 w-full h-24 bg-gradient-to-t from-terminal-bg to-transparent z-10 pointer-events-none" />
    </section>
  );
}
