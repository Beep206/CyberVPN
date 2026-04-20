import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { getPartnerSurfaceContext } from '@/features/storefront-shell/lib/server-surface-context';
import { StorefrontHomePage } from '@/features/storefront-shell/components/storefront-home-page';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Storefront.meta');
  const surfaceContext = await getPartnerSurfaceContext();

  if (surfaceContext.family !== 'storefront') {
    return withSiteMetadata(
      {
        title: 'CyberVPN Partner Portal',
        description: 'Partner workspace access.',
      },
      {
        locale,
        routeType: 'private',
      },
    );
  }

  return withSiteMetadata(
    {
      title: t('homeTitle', { brandName: surfaceContext.brandName }),
      description: t('homeDescription', { brandName: surfaceContext.brandName }),
    },
    {
      locale,
      canonicalPath: '/',
      routeType: 'public',
    },
  );
}

export default async function StorefrontHomeRoute({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const surfaceContext = await getPartnerSurfaceContext();

  if (surfaceContext.family !== 'storefront') {
    redirect(`/${locale}/login`);
  }

  const t = await getCachedTranslations(locale, 'Storefront.home');

  return (
    <StorefrontHomePage
      surfaceContext={surfaceContext}
      labels={{
        eyebrow: t('eyebrow'),
        title: t('title', { brandName: surfaceContext.brandName }),
        subtitle: t('subtitle', { brandName: surfaceContext.brandName, realmKey: surfaceContext.authRealmKey }),
        checkoutCta: t('checkoutCta'),
        legalCta: t('legalCta'),
        supportCta: t('supportCta'),
        loginCta: t('loginCta'),
        merchantLabel: t('merchantLabel'),
        supportLabel: t('supportLabel'),
        communicationLabel: t('communicationLabel'),
        realmLabel: t('realmLabel'),
        storefrontKeyLabel: t('storefrontKeyLabel'),
        hostLabel: t('hostLabel'),
        billingDescriptorLabel: t('billingDescriptorLabel'),
        refundModelLabel: t('refundModelLabel'),
        chargebackModelLabel: t('chargebackModelLabel'),
      }}
    />
  );
}
