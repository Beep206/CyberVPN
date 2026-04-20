import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { getPartnerSurfaceContext } from '@/features/storefront-shell/lib/server-surface-context';
import { StorefrontLegalDocumentsShell } from '@/features/storefront-shell/components/storefront-legal-documents-shell';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Storefront.meta');
  const surfaceContext = await getPartnerSurfaceContext();

  return withSiteMetadata(
    {
      title: surfaceContext.family === 'storefront'
        ? t('legalTitle', { brandName: surfaceContext.brandName })
        : 'Storefront legal context',
      description: surfaceContext.family === 'storefront'
        ? t('legalDescription', { brandName: surfaceContext.brandName })
        : 'Storefront legal context.',
    },
    {
      locale,
      canonicalPath: '/legal-docs',
      routeType: 'public',
    },
  );
}

export default async function StorefrontLegalRoute({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const surfaceContext = await getPartnerSurfaceContext();

  if (surfaceContext.family !== 'storefront') {
    redirect(`/${locale}/login`);
  }

  const t = await getCachedTranslations(locale, 'Storefront.legal');

  return (
    <StorefrontLegalDocumentsShell
      surfaceContext={surfaceContext}
      locale={locale}
      labels={{
        eyebrow: t('eyebrow'),
        title: t('title', { brandName: surfaceContext.brandName }),
        subtitle: t('subtitle'),
        required: t('required'),
        optional: t('optional'),
        checkoutCta: t('checkoutCta'),
        supportCta: t('supportCta'),
        loading: 'Resolving legal document set...',
        empty: 'No legal documents were resolved for this storefront.',
      }}
    />
  );
}
