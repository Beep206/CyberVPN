import type { BreadcrumbList, SoftwareApplication } from 'schema-dts';
import { notFound } from 'next/navigation';
import { setRequestLocale } from 'next-intl/server';
import { getSeoUiLabels } from '@/content/seo/market-localization';
import { locales } from '@/i18n/config';
import { getDeviceEntries, getDeviceEntry } from '@/content/seo/devices';
import { JsonLd } from '@/shared/lib/json-ld';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import {
  buildBreadcrumbListStructuredData,
  buildSoftwareApplicationStructuredData,
} from '@/shared/lib/structured-data';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { SeoKnowledgeArticlePage } from '@/widgets/seo/knowledge-article-page';

export async function generateStaticParams() {
  const entries = await getDeviceEntries();

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
  const entry = await getDeviceEntry(slug, locale);

  if (!entry) {
    return withSiteMetadata(
      {
        title: 'Device setup not found',
        description: 'Requested device setup page is unavailable.',
      },
      {
        locale,
        routeType: 'private',
      },
    );
  }

  return withSiteMetadata(
    {
      title: `${entry.title} | CyberVPN Devices`,
      description: entry.description,
    },
    {
      locale,
      canonicalPath: entry.path,
      routeType: 'public',
    },
  );
}

export default async function DeviceDetailPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const labels = getSeoUiLabels(locale);

  const entry = await getDeviceEntry(slug, locale);

  if (!entry) {
    notFound();
  }

  const appStructuredData = buildSoftwareApplicationStructuredData({
    locale,
    path: entry.path,
    title: entry.title,
    description: entry.description,
    applicationCategory: entry.applicationCategory,
    operatingSystems: entry.operatingSystems,
    featureList: entry.featureList,
    offers: entry.offers,
    downloadPath: entry.downloadPath,
  });
  const breadcrumbStructuredData = buildBreadcrumbListStructuredData({
    locale,
    items: [
      { name: labels.home, path: '/' },
      { name: labels.devices, path: '/devices' },
      { name: entry.title, path: entry.path },
    ],
  });

  return (
    <>
      <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
        <PublicTerminalHeader />
        <SeoKnowledgeArticlePage
          entry={entry}
          backHref="/devices"
          backLabel={labels.backToDevices}
          labels={{
            nextAction: labels.nextAction,
            relatedRoutes: labels.relatedRoutes,
            updated: labels.updated,
          }}
        />
        <Footer />
      </main>

      <JsonLd<SoftwareApplication> data={appStructuredData} />
      <JsonLd<BreadcrumbList> data={breadcrumbStructuredData} />
    </>
  );
}
