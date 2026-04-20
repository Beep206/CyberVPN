import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { TeamAccessPage } from '@/features/partner-workspace/components/team-access-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('team.metaTitle'),
      description: t('team.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/team',
    },
  );
}

export default function TeamPage() {
  return <TeamAccessPage />;
}

