import { getCachedTranslations } from '@/i18n/server';
import { getPartnerSurfaceContext } from '@/features/storefront-shell/lib/server-surface-context';
import { StorefrontAuthBoundaryCard } from '@/features/storefront-shell/components/storefront-auth-boundary-card';
import RegisterClient from './register-client';

export default async function RegisterPage({
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
        title={t('registerBlockedTitle')}
        description={t('registerBlockedDescription')}
        primaryCtaLabel={t('continueSignIn')}
        secondaryCtaLabel={t('backHome')}
      />
    );
  }

  return <RegisterClient />;
}
