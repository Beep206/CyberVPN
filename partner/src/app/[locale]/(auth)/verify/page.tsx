import { Suspense } from 'react';
import { getCachedTranslations } from '@/i18n/server';
import { getPartnerSurfaceContext } from '@/features/storefront-shell/lib/server-surface-context';
import { StorefrontAuthBoundaryCard } from '@/features/storefront-shell/components/storefront-auth-boundary-card';
import { VerifyClient } from './verify-client';

export default async function VerifyPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const surfaceContext = await getPartnerSurfaceContext();

  if (surfaceContext.family === 'storefront') {
    const t = await getCachedTranslations(locale, 'Storefront.auth');

    return (
      <StorefrontAuthBoundaryCard
        title={t('verifyBlockedTitle')}
        description={t('verifyBlockedDescription')}
        primaryCtaLabel={t('continueSignIn')}
        secondaryCtaLabel={t('backHome')}
      />
    );
  }

  return (
    <Suspense fallback={null}>
      <VerifyClient />
    </Suspense>
  );
}
