import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { PartnerNotificationsPage } from '@/features/partner-portal-state/components/partner-notifications-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('notifications.metaTitle'),
      description: t('notifications.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/notifications',
    },
  );
}

export default function NotificationsPage() {
  return <PartnerNotificationsPage />;
}
