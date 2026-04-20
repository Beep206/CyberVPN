import { Suspense } from 'react';
import { getCachedTranslations } from '@/i18n/server';
import { getPartnerSurfaceContext } from '@/features/storefront-shell/lib/server-surface-context';
import { LoginClient } from './login-client';
import { StorefrontLoginClient } from '@/features/storefront-shell/components/storefront-login-client';

export default async function LoginPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const surfaceContext = await getPartnerSurfaceContext();

  if (surfaceContext.family === 'storefront') {
    const t = await getCachedTranslations(locale, 'Storefront.auth');

    return (
      <Suspense fallback={null}>
        <StorefrontLoginClient
          title={t('title', { brandName: surfaceContext.brandName })}
          subtitle={t('subtitle', { brandName: surfaceContext.brandName })}
        />
      </Suspense>
    );
  }

  return (
    <Suspense fallback={null}>
      <LoginClient />
    </Suspense>
  );
}
