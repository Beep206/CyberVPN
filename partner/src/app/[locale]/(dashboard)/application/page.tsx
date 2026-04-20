import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { ApplicationFoundationPage } from '@/features/partner-onboarding/components/application-foundation-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('application.metaTitle'),
      description: t('application.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/application',
    },
  );
}

export default function ApplicationPage() {
  return <ApplicationFoundationPage />;
}
