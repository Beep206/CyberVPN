import { ArrowRight, CheckCircle2 } from 'lucide-react';
import { Link } from '@/i18n/navigation';
import type { SeoHubContent } from '@/content/seo/types';

type SeoContentHubPageLabels = {
  hubIntent: string;
  readPage: string;
};

export function SeoContentHubPage({
  content,
  locale,
  labels,
}: {
  content: SeoHubContent;
  locale: string;
  labels?: SeoContentHubPageLabels;
}) {
  const resolvedLabels = labels ?? {
    hubIntent: 'Hub intent',
    readPage: 'Read page',
  };

  return (
    <section className="relative isolate overflow-hidden px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,rgba(0,255,255,0.12),transparent_35%),radial-gradient(circle_at_bottom_right,rgba(255,0,255,0.1),transparent_35%)]" />
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-10">
        <div className="grid gap-8 rounded-3xl border border-grid-line/40 bg-background/55 p-6 shadow-[0_0_120px_rgba(0,255,255,0.06)] backdrop-blur md:p-8 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-6">
            <span className="inline-flex items-center rounded-full border border-neon-cyan/40 bg-neon-cyan/10 px-3 py-1 text-xs font-mono uppercase tracking-[0.3em] text-neon-cyan">
              {content.badge}
            </span>
            <div className="space-y-4">
              <h1 className="max-w-4xl text-4xl font-black tracking-tight text-white md:text-5xl">
                {content.title}
              </h1>
              <p className="max-w-3xl text-base leading-7 text-muted-foreground md:text-lg">
                {content.description}
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {content.proofPoints.map((proofPoint) => (
                <div
                  key={proofPoint}
                  className="rounded-2xl border border-neon-purple/20 bg-terminal-bg/70 px-4 py-3 text-sm font-mono text-neon-purple"
                >
                  {proofPoint}
                </div>
              ))}
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {content.ctaLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  locale={locale}
                  className="group rounded-2xl border border-neon-cyan/25 bg-neon-cyan/10 px-4 py-4 transition-colors hover:border-neon-cyan/60 hover:bg-neon-cyan/15"
                  data-seo-cta={link.seoCta}
                  data-seo-zone={link.seoZone}
                >
                  <span className="flex items-center justify-between gap-4 text-sm font-semibold text-white">
                    {link.label}
                    <ArrowRight className="h-4 w-4 text-neon-cyan transition-transform group-hover:translate-x-1" />
                  </span>
                  <span className="mt-2 block text-sm leading-6 text-muted-foreground">
                    {link.description}
                  </span>
                </Link>
              ))}
            </div>
          </div>

            <div className="rounded-3xl border border-neon-purple/25 bg-terminal-bg/80 p-6">
            <div className="mb-4 text-xs font-mono uppercase tracking-[0.3em] text-neon-purple">
              {resolvedLabels.hubIntent}
            </div>
            <div className="space-y-4">
              {content.bullets.map((bullet) => (
                <div key={bullet} className="flex items-start gap-3">
                  <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-matrix-green" />
                  <p className="text-sm leading-6 text-muted-foreground">{bullet}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {content.cards.map((card) => (
            <article
              key={card.slug}
              className="group flex h-full flex-col rounded-3xl border border-grid-line/40 bg-background/65 p-6 transition-colors hover:border-neon-cyan/45"
            >
              <div className="mb-4 text-xs font-mono uppercase tracking-[0.3em] text-neon-cyan/80">
                {card.eyebrow}
              </div>
              <h2 className="text-2xl font-bold tracking-tight text-white">{card.title}</h2>
              <p className="mt-4 flex-1 text-sm leading-7 text-muted-foreground">
                {card.description}
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                {card.stats.map((stat) => (
                  <span
                    key={stat}
                    className="rounded-full border border-grid-line/40 bg-terminal-bg/75 px-3 py-1 text-xs font-mono text-muted-foreground"
                  >
                    {stat}
                  </span>
                ))}
              </div>
              <Link
                href={card.path}
                locale={locale}
                className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-neon-cyan"
                data-seo-cta={`hub_card_${card.slug}`}
                data-seo-zone="hub_cards"
              >
                {resolvedLabels.readPage}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
