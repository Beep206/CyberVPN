import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { LegalDocumentsPage } from '@/features/partner-legal/components/legal-documents-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Partner');

  return withSiteMetadata(
    {
      title: t('legal.metaTitle'),
      description: t('legal.metaDescription'),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: '/legal',
    },
  );
}

export default function LegalPage() {
  return <LegalDocumentsPage />;
}

