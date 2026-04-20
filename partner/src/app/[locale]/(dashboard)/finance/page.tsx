import { Suspense } from 'react';
import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { FinanceOperationsPageEntry } from '@/features/partner-finance/components/finance-operations-page-entry';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('finance.metaTitle'),
      description: t('finance.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/finance',
    },
  );
}

export default function FinanceRoutePage() {
  return (
    <Suspense fallback={null}>
      <FinanceOperationsPageEntry />
    </Suspense>
  );
}
