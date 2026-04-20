import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { getPartnerSurfaceContext } from '@/features/storefront-shell/lib/server-surface-context';
import { StorefrontCheckoutShell } from '@/features/storefront-shell/components/storefront-checkout-shell';

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
        ? t('checkoutTitle', { brandName: surfaceContext.brandName })
        : 'Partner checkout',
      description: surfaceContext.family === 'storefront'
        ? t('checkoutDescription', { brandName: surfaceContext.brandName })
        : 'Storefront checkout shell.',
    },
    {
      locale,
      canonicalPath: '/checkout',
      routeType: 'public',
    },
  );
}

export default async function StorefrontCheckoutRoute({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const surfaceContext = await getPartnerSurfaceContext();

  if (surfaceContext.family !== 'storefront') {
    redirect(`/${locale}/login`);
  }

  const t = await getCachedTranslations(locale, 'Storefront.checkout');

  return (
    <StorefrontCheckoutShell
      surfaceContext={surfaceContext}
      labels={{
        title: t('title'),
        subtitle: t('subtitle', { brandName: surfaceContext.brandName }),
        empty: t('empty'),
        checkoutAction: t('checkoutAction'),
        checkoutPending: t('checkoutPending'),
        signInCta: t('signInCta'),
        legalNotice: t('legalNotice'),
        currentEntitlementLabel: t('currentEntitlementLabel'),
        currentServiceStateLabel: t('currentServiceStateLabel'),
        orderReadyLabel: t('orderReadyLabel'),
        orderIdLabel: t('orderIdLabel'),
        attemptStatusLabel: t('attemptStatusLabel'),
        paymentLinkLabel: t('paymentLinkLabel'),
        legalLinkLabel: t('legalLinkLabel'),
        supportLinkLabel: t('supportLinkLabel'),
        pricebookLabel: t('pricebookLabel'),
        includedAddonsLabel: t('includedAddonsLabel'),
      }}
    />
  );
}
