import { SupportTicketsRoute } from '@/features/support/components/SupportTicketsRoute';
import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'MiniApp.support.meta');

  return withSiteMetadata({
    title: t('title'),
    description: t('description'),
  }, {
    locale,
    routeType: 'private',
  });
}

export default function MiniAppSupportPage() {
  return <SupportTicketsRoute variant="miniapp" />;
}
