import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { IntegrationsConsolePage } from '@/features/partner-integrations/components/integrations-console-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('integrations.metaTitle'),
      description: t('integrations.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/integrations',
    },
  );
}

export default function IntegrationsRoutePage() {
  return <IntegrationsConsolePage />;
}
