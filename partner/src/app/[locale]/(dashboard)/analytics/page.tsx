import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { AnalyticsExportsPage } from '@/features/partner-reporting/components/analytics-exports-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('analytics.metaTitle'),
      description: t('analytics.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/analytics',
    },
  );
}

export default function AnalyticsRoutePage() {
  return <AnalyticsExportsPage />;
}
