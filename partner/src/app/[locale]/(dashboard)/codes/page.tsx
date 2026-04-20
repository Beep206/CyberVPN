import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { CodesTrackingPage } from '@/features/partner-commercial/components/codes-tracking-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('codes.metaTitle'),
      description: t('codes.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/codes',
    },
  );
}

export default function CodesRoutePage() {
  return <CodesTrackingPage />;
}
