import { Suspense } from 'react';
import { connection } from 'next/server';
import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { SettingsFoundationPageEntry } from '@/features/partner-settings/components/settings-foundation-page-entry';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('settings.metaTitle'),
      description: t('settings.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/settings',
    },
  );
}

export default async function SettingsPage() {
  await connection();

  return (
    <Suspense fallback={null}>
      <SettingsFoundationPageEntry />
    </Suspense>
  );
}
