import { Send, TerminalSquare } from 'lucide-react';
import { getLocale, getTranslations } from 'next-intl/server';
import { Link } from '@/i18n/navigation';
import { Reveal } from '@/shared/ui/reveal';
import { ScrambleText } from '@/shared/ui/scramble-text';

export async function HelpContact({ locale: providedLocale }: { locale?: string } = {}) {
  const locale = providedLocale ?? await getLocale();
  const t = await getTranslations({ locale, namespace: 'HelpCenter' });

  return (
    <section className="relative w-full overflow-hidden border border-neon-purple/30 bg-terminal-card/40 backdrop-blur-sm p-8 md:p-12 mb-20 rounded-xl group hover:border-neon-purple/60 transition-colors">
      <div className="absolute inset-0 bg-grid-white/[0.01] bg-[size:30px_30px] pointer-events-none" />
      <div className="absolute right-0 top-0 w-64 h-64 bg-neon-purple/5 blur-[120px] rounded-full pointer-events-none group-hover:bg-neon-purple/10 transition-colors" />

      <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-10">
        <div className="flex-1 text-center md:text-left">
          <Reveal variant="left">
            <h2 className="text-3xl font-display font-bold text-foreground tracking-widest mb-4">
              <ScrambleText text={t('contact_title')} />
            </h2>
            <p className="text-muted-foreground font-mono max-w-xl">
              {t('contact_desc')}
            </p>
          </Reveal>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
          <Reveal delay={0.1}>
            <Link
              href="/contact"
              locale={locale}
              className="group relative inline-flex h-14 flex-1 items-center justify-center overflow-hidden rounded-md border border-neon-pink/50 bg-neon-pink/10 px-8 font-bold tracking-wide text-neon-pink transition-all hover:bg-neon-pink/20 sm:flex-none"
              data-seo-cta="contact"
              data-seo-zone="help_contact"
            >
              <span className="absolute inset-0 bg-neon-pink/10 group-hover:translate-x-full transition-transform duration-500 ease-out" style={{ transformOrigin: 'left' }} />
              <TerminalSquare className="mr-3 h-5 w-5 relative z-10" />
              <span className="relative z-10">{t('contact_button_ticket')}</span>
            </Link>
          </Reveal>

          <Reveal delay={0.2}>
            <a
              href="https://t.me/cybervpn_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="group inline-flex h-14 flex-1 items-center justify-center rounded-md bg-matrix-green px-8 font-bold tracking-wide text-black shadow-[0_0_15px_rgba(0,255,136,0.3)] transition-all hover:bg-matrix-green/80 hover:shadow-[0_0_25px_rgba(0,255,136,0.5)] sm:flex-none"
              data-seo-cta="telegram"
              data-seo-zone="help_contact"
            >
              <Send className="mr-3 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              {t('contact_button_telegram')}
            </a>
          </Reveal>
        </div>
      </div>

      <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-neon-purple/50" />
      <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-neon-purple/50" />
      <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-neon-purple/50" />
      <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-neon-purple/50" />
    </section>
  );
}
