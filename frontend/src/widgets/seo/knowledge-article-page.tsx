import { ArrowRight, ShieldCheck } from 'lucide-react';
import { Link } from '@/i18n/navigation';
import type {
  SeoArticleEntry,
  SeoCallToAction,
  SeoResourceLink,
  SeoStaticKnowledgePage,
} from '@/content/seo/types';

type KnowledgeEntry = SeoArticleEntry | SeoStaticKnowledgePage;

function renderActionLink(link: SeoCallToAction, locale: string) {
  return (
    <Link
      key={link.href}
      href={link.href}
      locale={locale}
      className="group rounded-2xl border border-neon-cyan/25 bg-neon-cyan/10 px-4 py-4 transition-colors hover:border-neon-cyan/60 hover:bg-neon-cyan/15"
      data-seo-cta={link.seoCta}
      data-seo-zone={link.seoZone}
    >
      <span className="flex items-center justify-between gap-3 text-sm font-semibold text-white">
        {link.label}
        <ArrowRight className="h-4 w-4 text-neon-cyan transition-transform group-hover:translate-x-1" />
      </span>
      <span className="mt-2 block text-sm leading-6 text-muted-foreground">
        {link.description}
      </span>
    </Link>
  );
}

function renderResourceLink(link: SeoResourceLink, locale: string) {
  return (
    <Link
      key={link.href}
      href={link.href}
      locale={locale}
      className="rounded-2xl border border-grid-line/35 bg-terminal-bg/70 px-4 py-4 transition-colors hover:border-neon-purple/45"
      data-seo-cta={`related_${link.href.replace(/\//g, '_')}`}
      data-seo-zone="knowledge_related"
    >
      <span className="block text-sm font-semibold text-white">{link.label}</span>
      <span className="mt-2 block text-sm leading-6 text-muted-foreground">
        {link.description}
      </span>
    </Link>
  );
}

export function SeoKnowledgeArticlePage({
  entry,
  locale,
  backHref,
  backLabel,
  labels,
}: {
  entry: KnowledgeEntry;
  locale: string;
  backHref: string;
  backLabel: string;
  labels?: {
    nextAction: string;
    relatedRoutes: string;
    updated: string;
  };
}) {
  const resolvedLabels = labels ?? {
    nextAction: 'Next action',
    relatedRoutes: 'Related routes',
    updated: 'Updated',
  };

  return (
    <section className="relative isolate overflow-hidden px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top,rgba(0,255,255,0.12),transparent_30%),radial-gradient(circle_at_bottom_left,rgba(255,0,255,0.1),transparent_35%)]" />
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-10">
        <div className="rounded-3xl border border-grid-line/40 bg-background/60 p-6 shadow-[0_0_120px_rgba(0,255,255,0.06)] backdrop-blur md:p-8">
          <Link
            href={backHref}
            locale={locale}
            className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-[0.3em] text-neon-cyan"
            data-seo-cta="knowledge_back"
            data-seo-zone="knowledge_header"
          >
            <ArrowRight className="h-4 w-4 rotate-180" />
            {backLabel}
          </Link>

          <div className="mt-6 grid gap-8 lg:grid-cols-[1.3fr_0.7fr]">
            <div className="space-y-6">
              <span className="inline-flex items-center rounded-full border border-neon-purple/40 bg-neon-purple/10 px-3 py-1 text-xs font-mono uppercase tracking-[0.3em] text-neon-purple">
                {entry.badge}
              </span>
              <div className="space-y-4">
                <h1 className="max-w-4xl text-4xl font-black tracking-tight text-white md:text-5xl">
                  {entry.title}
                </h1>
                <p className="max-w-3xl text-base leading-7 text-muted-foreground md:text-lg">
                  {entry.description}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full border border-grid-line/40 bg-terminal-bg/75 px-3 py-1 text-xs font-mono text-muted-foreground">
                  {entry.readingTime}
                </span>
                <span className="rounded-full border border-grid-line/40 bg-terminal-bg/75 px-3 py-1 text-xs font-mono text-muted-foreground">
                  {resolvedLabels.updated} {entry.updatedAt}
                </span>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                {entry.heroPoints.map((heroPoint) => (
                  <div
                    key={heroPoint}
                    className="rounded-2xl border border-neon-cyan/20 bg-terminal-bg/80 px-4 py-4 text-sm leading-6 text-muted-foreground"
                  >
                    {heroPoint}
                  </div>
                ))}
              </div>
            </div>

            <aside className="rounded-3xl border border-neon-cyan/20 bg-terminal-bg/80 p-6">
              <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-[0.3em] text-neon-cyan">
                <ShieldCheck className="h-4 w-4" />
                {resolvedLabels.nextAction}
              </div>
              <div className="mt-4 grid gap-3">
                {entry.ctaLinks.map((link) => renderActionLink(link, locale))}
              </div>
            </aside>
          </div>
        </div>

        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-6">
            {entry.sections.map((section) => (
              <article
                key={section.title}
                className="rounded-3xl border border-grid-line/35 bg-background/60 p-6"
              >
                <h2 className="text-2xl font-bold tracking-tight text-white">{section.title}</h2>
                <div className="mt-4 space-y-4 text-sm leading-7 text-muted-foreground md:text-base">
                  {section.paragraphs.map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}
                </div>
                {section.bullets?.length ? (
                  <ul className="mt-5 space-y-3">
                    {section.bullets.map((bullet) => (
                      <li key={bullet} className="flex items-start gap-3 text-sm text-muted-foreground">
                        <span className="mt-2 h-1.5 w-1.5 rounded-full bg-neon-cyan" />
                        <span>{bullet}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </article>
            ))}
          </div>

          <aside className="space-y-4">
            <div className="rounded-3xl border border-neon-purple/20 bg-background/60 p-6">
              <div className="text-xs font-mono uppercase tracking-[0.3em] text-neon-purple">
                {resolvedLabels.relatedRoutes}
              </div>
              <div className="mt-4 grid gap-3">
                {entry.relatedLinks.map((link) => renderResourceLink(link, locale))}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
