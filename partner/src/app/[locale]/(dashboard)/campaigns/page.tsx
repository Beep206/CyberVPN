import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { CampaignsEnablementPage } from '@/features/partner-commercial/components/campaigns-enablement-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('campaigns.metaTitle'),
      description: t('campaigns.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/campaigns',
    },
  );
}

export default function CampaignsRoutePage() {
  return <CampaignsEnablementPage />;
}
