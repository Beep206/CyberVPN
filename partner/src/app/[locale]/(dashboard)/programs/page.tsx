import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { ProgramsPage } from '@/features/partner-workspace/components/programs-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('programs.metaTitle'),
      description: t('programs.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/programs',
    },
  );
}

export default function ProgramsRoutePage() {
  return <ProgramsPage />;
}

