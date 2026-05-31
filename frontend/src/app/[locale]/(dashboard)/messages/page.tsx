import { Suspense } from 'react';
import { CustomerMessagingRoute } from '@/features/messaging/components/CustomerMessagingRoute';
import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Messaging.meta');

  return withSiteMetadata({
    title: t('title'),
    description: t('description'),
  }, {
    locale,
    routeType: 'private',
  });
}

export default function MessagesPage() {
  return (
    <Suspense
      fallback={
        <div className="grid gap-4 lg:grid-cols-[minmax(300px,390px)_1fr]">
          <div className="h-96 animate-pulse rounded-lg border border-grid-line/30 bg-terminal-surface/45" />
          <div className="h-96 animate-pulse rounded-lg border border-grid-line/30 bg-terminal-surface/55" />
        </div>
      }
    >
      <CustomerMessagingRoute />
    </Suspense>
  );
}
