import type { HelpCategoryKnowledge } from '@/widgets/help-faq-server';

export function HelpCategoriesServer({
  categories,
  title,
  intro,
}: {
  categories: HelpCategoryKnowledge[];
  title: string;
  intro: string;
}) {
  return (
    <section className="relative w-full">
      <div className="mb-4 flex items-center gap-4">
        <div className="h-px flex-1 bg-terminal-border" />
        <h2 className="text-2xl font-display font-bold uppercase tracking-widest text-foreground">
          {title}
        </h2>
        <div className="h-px flex-1 bg-terminal-border" />
      </div>

      <p className="mb-10 max-w-3xl text-sm font-mono leading-relaxed tracking-wide text-muted-foreground">
        {intro}
      </p>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {categories.map((category, index) => (
          <a
            key={category.id}
            href={`?category=${category.id}#${category.anchorId}`}
            className={`group block h-full rounded-2xl border bg-terminal-surface/80 p-6 transition-all duration-300 hover:-translate-y-1 hover:bg-terminal-card/90 ${category.borderClass}`}
          >
            <p className="mb-4 font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground/60">
              NODE_{String(index + 1).padStart(2, '0')}
            </p>
            <h3 className={`mb-3 text-xl font-display font-bold ${category.accentClass}`}>
              {category.title}
            </h3>
            <p className="text-sm leading-relaxed text-muted-foreground font-mono">
              {category.description}
            </p>
            <p className="mt-6 font-mono text-xs uppercase tracking-[0.25em] text-foreground/70 transition-colors group-hover:text-foreground">
              Open answer block
            </p>
          </a>
        ))}
      </div>
    </section>
  );
}
