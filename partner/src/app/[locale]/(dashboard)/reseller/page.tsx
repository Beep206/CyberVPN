import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { ResellerConsolePage } from '@/features/partner-reseller/components/reseller-console-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('reseller.metaTitle'),
      description: t('reseller.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/reseller',
    },
  );
}

export default function ResellerRoutePage() {
  return <ResellerConsolePage />;
}
