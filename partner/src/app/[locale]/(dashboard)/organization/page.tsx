import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { OrganizationStarterPage } from '@/features/partner-onboarding/components/organization-starter-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('organization.metaTitle'),
      description: t('organization.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/organization',
    },
  );
}

export default function OrganizationPage() {
  return <OrganizationStarterPage />;
}
