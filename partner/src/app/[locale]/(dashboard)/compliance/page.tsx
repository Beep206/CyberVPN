import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { ComplianceCenterPage } from '@/features/partner-compliance/components/compliance-center-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('compliance.metaTitle'),
      description: t('compliance.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/compliance',
    },
  );
}

export default function ComplianceRoutePage() {
  return <ComplianceCenterPage />;
}
