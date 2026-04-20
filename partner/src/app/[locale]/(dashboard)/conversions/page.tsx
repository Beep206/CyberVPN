import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { ConversionsOrdersPage } from '@/features/partner-operations/components/conversions-orders-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('conversions.metaTitle'),
      description: t('conversions.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/conversions',
    },
  );
}

export default function ConversionsRoutePage() {
  return <ConversionsOrdersPage />;
}
