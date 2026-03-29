import { Suspense } from 'react';
import { cacheLife } from 'next/cache';
import { ScopedIntlProvider } from '@/app/providers/scoped-intl-provider';
import { SmoothScrollProvider } from '@/app/providers/smooth-scroll-provider';
import { MARKETING_CLIENT_NAMESPACES } from '@/i18n/client-namespaces';

async function CachedMarketingShell({ children }: { children: React.ReactNode }) {
  'use cache';
  cacheLife('hours');

  return <>{children}</>;
}

export default async function MarketingLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  return (
    <ScopedIntlProvider locale={locale} namespaces={MARKETING_CLIENT_NAMESPACES}>
      <SmoothScrollProvider />
      <Suspense fallback={null}>
        <CachedMarketingShell>{children}</CachedMarketingShell>
      </Suspense>
    </ScopedIntlProvider>
  );
}
