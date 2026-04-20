import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { PartnerCasesPage } from '@/features/partner-portal-state/components/partner-cases-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('cases.metaTitle'),
      description: t('cases.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/cases',
    },
  );
}

export default function CasesPage() {
  return <PartnerCasesPage />;
}
