import type { BreadcrumbList, TechArticle } from 'schema-dts';
import { setRequestLocale } from 'next-intl/server';
import { getSeoUiLabels } from '@/content/seo/market-localization';
import { getTrustCenterContent } from '@/content/seo/trust';
import { JsonLd } from '@/shared/lib/json-ld';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import {
  buildBreadcrumbListStructuredData,
  buildTechArticleStructuredData,
} from '@/shared/lib/structured-data';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { SeoKnowledgeArticlePage } from '@/widgets/seo/knowledge-article-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const content = await getTrustCenterContent(locale);

  return withSiteMetadata(
    {
      title: `${content.title} | CyberVPN`,
      description: content.description,
    },
    {
      locale,
      canonicalPath: content.path,
      routeType: 'public',
    },
  );
}

export default async function TrustPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const labels = getSeoUiLabels(locale);

  const content = await getTrustCenterContent(locale);
  const articleStructuredData = buildTechArticleStructuredData({
    locale,
    path: content.path,
    title: content.title,
    description: content.description,
    sections: content.sections.map((section) => section.title),
  });
  const breadcrumbStructuredData = buildBreadcrumbListStructuredData({
    locale,
    items: [
      { name: labels.home, path: '/' },
      { name: labels.trustCenter, path: content.path },
    ],
  });

  return (
    <>
      <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
        <PublicTerminalHeader />
        <SeoKnowledgeArticlePage
          entry={content}
          backHref="/"
          backLabel={labels.backToHomepage}
          labels={{
            nextAction: labels.nextAction,
            relatedRoutes: labels.relatedRoutes,
            updated: labels.updated,
          }}
        />
        <Footer />
      </main>

      <JsonLd<TechArticle> data={articleStructuredData} />
      <JsonLd<BreadcrumbList> data={breadcrumbStructuredData} />
    </>
  );
}
