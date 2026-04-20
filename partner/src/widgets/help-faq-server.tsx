import { getTranslations } from 'next-intl/server';

export const HELP_CATEGORY_IDS = [
  'getting_started',
  'troubleshooting',
  'billing',
  'security',
] as const;

export type HelpCategoryId = (typeof HELP_CATEGORY_IDS)[number];

export type HelpFaqItem = {
  question: string;
  answer: string;
};

export type HelpCategoryKnowledge = {
  id: HelpCategoryId;
  anchorId: string;
  title: string;
  description: string;
  accentClass: string;
  borderClass: string;
  faqs: HelpFaqItem[];
};

const CATEGORY_STYLES: Record<
  HelpCategoryId,
  { accentClass: string; borderClass: string }
> = {
  getting_started: {
    accentClass: 'text-matrix-green',
    borderClass: 'border-matrix-green/30',
  },
  troubleshooting: {
    accentClass: 'text-neon-cyan',
    borderClass: 'border-neon-cyan/30',
  },
  billing: {
    accentClass: 'text-neon-pink',
    borderClass: 'border-neon-pink/30',
  },
  security: {
    accentClass: 'text-neon-purple',
    borderClass: 'border-neon-purple/30',
  },
};

export async function getHelpKnowledge(locale?: string): Promise<HelpCategoryKnowledge[]> {
  const t = locale
    ? await getTranslations({ locale, namespace: 'HelpCenter' })
    : await getTranslations('HelpCenter');

  return HELP_CATEGORY_IDS.map((id) => ({
    id,
    anchorId: `faq-${id}`,
    title: t(`category_${id}`),
    description: t(`category_${id}_desc`),
    accentClass: CATEGORY_STYLES[id].accentClass,
    borderClass: CATEGORY_STYLES[id].borderClass,
    faqs: [1, 2, 3].map((index) => ({
      question: t(`faq_${id}_${index}_q`),
      answer: t(`faq_${id}_${index}_a`),
    })),
  }));
}

export function HelpFaqServer({
  categories,
  title,
  intro,
}: {
  categories: HelpCategoryKnowledge[];
  title: string;
  intro: string;
}) {
  return (
    <section id="faq" className="relative w-full max-w-6xl mx-auto mb-32 scroll-mt-32">
      <div className="mb-6 flex items-center gap-4">
        <div className="h-px flex-1 bg-terminal-border" />
        <h2 className="text-2xl font-display font-bold uppercase tracking-widest text-foreground">
          {title}
        </h2>
        <div className="h-px flex-1 bg-terminal-border" />
      </div>

      <p className="mb-12 max-w-3xl text-sm font-mono leading-relaxed tracking-wide text-muted-foreground">
        {intro}
      </p>

      <div className="space-y-10">
        {categories.map((category, categoryIndex) => (
          <article
            key={category.id}
            id={category.anchorId}
            className={`scroll-mt-32 rounded-2xl border bg-terminal-card/50 p-6 backdrop-blur-sm md:p-8 ${category.borderClass}`}
          >
            <div className="mb-8 flex flex-col gap-3 border-b border-terminal-border/30 pb-6 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="mb-2 font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground/60">
                  MODULE_{String(categoryIndex + 1).padStart(2, '0')}
                </p>
                <h3 className={`text-2xl font-display font-bold ${category.accentClass}`}>
                  {category.title}
                </h3>
              </div>
              <p className="max-w-2xl text-sm font-mono leading-relaxed text-muted-foreground">
                {category.description}
              </p>
            </div>

            <div className="space-y-4">
              {category.faqs.map((faq, faqIndex) => (
                <div
                  key={faq.question}
                  className="rounded-xl border border-terminal-border/30 bg-black/20 p-5"
                >
                  <p className="mb-3 font-mono text-xs uppercase tracking-[0.25em] text-muted-foreground/60">
                    QUERY_{String(categoryIndex + 1).padStart(2, '0')}_{faqIndex + 1}
                  </p>
                  <h4 className="mb-3 text-lg font-display font-semibold text-foreground">
                    {faq.question}
                  </h4>
                  <p className="text-sm leading-7 text-muted-foreground font-mono">
                    {faq.answer}
                  </p>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
