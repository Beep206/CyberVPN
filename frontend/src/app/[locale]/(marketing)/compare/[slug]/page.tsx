import type { BreadcrumbList, TechArticle } from 'schema-dts';
import { notFound } from 'next/navigation';
import { setRequestLocale } from 'next-intl/server';
import { getSeoUiLabels } from '@/content/seo/market-localization';
import { locales } from '@/i18n/config';
import { getComparisonEntries, getComparisonEntry } from '@/content/seo/comparisons';
import { JsonLd } from '@/shared/lib/json-ld';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import {
  buildBreadcrumbListStructuredData,
  buildTechArticleStructuredData,
} from '@/shared/lib/structured-data';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { SeoKnowledgeArticlePage } from '@/widgets/seo/knowledge-article-page';

export async function generateStaticParams() {
  const entries = await getComparisonEntries();

  return locales.flatMap((locale) =>
    entries.map((entry) => ({
      locale,
      slug: entry.slug,
    })),
  );
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  const entry = await getComparisonEntry(slug, locale);

  if (!entry) {
    return withSiteMetadata(
      {
        title: 'Comparison not found',
        description: 'Requested comparison is unavailable.',
      },
      {
        locale,
        routeType: 'private',
      },
    );
  }

  return withSiteMetadata(
    {
      title: `${entry.title} | CyberVPN Compare`,
      description: entry.description,
    },
    {
      locale,
      canonicalPath: entry.path,
      routeType: 'public',
    },
  );
}

export default async function CompareDetailPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const labels = getSeoUiLabels(locale);

  const entry = await getComparisonEntry(slug, locale);

  if (!entry) {
    notFound();
  }

  const articleStructuredData = buildTechArticleStructuredData({
    locale,
    path: entry.path,
    title: entry.title,
    description: entry.description,
    sections: entry.sections.map((section) => section.title),
  });
  const breadcrumbStructuredData = buildBreadcrumbListStructuredData({
    locale,
    items: [
      { name: labels.home, path: '/' },
      { name: labels.compare, path: '/compare' },
      { name: entry.title, path: entry.path },
    ],
  });

  return (
    <>
      <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
        <PublicTerminalHeader locale={locale} />
        <SeoKnowledgeArticlePage
          entry={entry}
          locale={locale}
          backHref="/compare"
          backLabel={labels.backToCompare}
          labels={{
            nextAction: labels.nextAction,
            relatedRoutes: labels.relatedRoutes,
            updated: labels.updated,
          }}
        />
        <Footer locale={locale} />
      </main>

      <JsonLd<TechArticle> data={articleStructuredData} />
      <JsonLd<BreadcrumbList> data={breadcrumbStructuredData} />
    </>
  );
}
