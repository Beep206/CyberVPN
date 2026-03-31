import type { BreadcrumbList, CollectionPage } from 'schema-dts';
import { setRequestLocale } from 'next-intl/server';
import { getDevicesHubContent } from '@/content/seo/devices';
import { getSeoUiLabels } from '@/content/seo/market-localization';
import { JsonLd } from '@/shared/lib/json-ld';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import {
  buildBreadcrumbListStructuredData,
  buildCollectionPageStructuredData,
} from '@/shared/lib/structured-data';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { SeoContentHubPage } from '@/widgets/seo/content-hub-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const hub = await getDevicesHubContent(locale);

  return withSiteMetadata(
    {
      title: `${hub.title} | CyberVPN`,
      description: hub.description,
    },
    {
      locale,
      canonicalPath: hub.path,
      routeType: 'public',
    },
  );
}

export default async function DevicesPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const labels = getSeoUiLabels(locale);

  const hub = await getDevicesHubContent(locale);
  const collectionStructuredData = buildCollectionPageStructuredData({
    locale,
    path: hub.path,
    title: hub.title,
    description: hub.description,
    items: hub.cards.map((card) => ({ name: card.title, path: card.path })),
  });
  const breadcrumbStructuredData = buildBreadcrumbListStructuredData({
    locale,
    items: [
      { name: labels.home, path: '/' },
      { name: labels.devices, path: hub.path },
    ],
  });

  return (
    <>
      <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
        <PublicTerminalHeader locale={locale} />
        <SeoContentHubPage
          content={hub}
          locale={locale}
          labels={{ hubIntent: labels.hubIntent, readPage: labels.readPage }}
        />
        <Footer locale={locale} />
      </main>

      <JsonLd<CollectionPage> data={collectionStructuredData} />
      <JsonLd<BreadcrumbList> data={breadcrumbStructuredData} />
    </>
  );
}
