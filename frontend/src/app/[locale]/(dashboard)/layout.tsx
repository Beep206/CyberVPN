import type { SoftwareApplication } from 'schema-dts';
import { getTranslations } from 'next-intl/server';
import { QueryProvider } from '@/app/providers/query-provider';
import { ScopedIntlProvider } from '@/app/providers/scoped-intl-provider';
import { DASHBOARD_CLIENT_NAMESPACES } from '@/i18n/client-namespaces';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { AuthGuard } from '@/features/auth/components';
import { JsonLd } from '@/shared/lib/json-ld';
import { ErrorBoundary } from '@/shared/ui/error-boundary';
import { Scanlines } from '@/shared/ui/atoms/scanlines';
import { CyberSidebar } from '@/widgets/cyber-sidebar';
import { MobileSidebar } from '@/widgets/mobile-sidebar';
import { TerminalHeader } from '@/widgets/terminal-header';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Dashboard.meta' });

  return withSiteMetadata({
    title: t('title'),
    description: t('description'),
  });
}

export default async function DashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  return (
    <ScopedIntlProvider locale={locale} namespaces={DASHBOARD_CLIENT_NAMESPACES}>
      <QueryProvider>
        <AuthGuard>
          <JsonLd<SoftwareApplication>
            data={{
              '@context': 'https://schema.org',
              '@type': 'SoftwareApplication',
              name: 'CyberVPN',
              applicationCategory: 'SecurityApplication',
              operatingSystem: 'Web, Android, iOS',
              offers: {
                '@type': 'Offer',
                price: '0',
                priceCurrency: 'USD',
              },
            }}
          />

          <div className="flex h-screen w-full overflow-hidden bg-terminal-bg text-foreground">
            <a
              href="#main-content"
              className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:bg-neon-cyan focus:text-black focus:px-4 focus:py-2 focus:rounded-sm focus:font-mono focus:text-sm"
            >
              Skip to main content
            </a>

            <Scanlines />

            <ErrorBoundary label="Sidebar">
              <CyberSidebar />
            </ErrorBoundary>

            <MobileSidebar />

            <div className="relative flex flex-1 flex-col overflow-hidden md:pl-64">
              <ErrorBoundary label="Header">
                <TerminalHeader performanceMode="always" />
              </ErrorBoundary>

              <main
                id="main-content"
                tabIndex={-1}
                aria-live="polite"
                data-lenis-prevent="true"
                className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden relative p-4 md:p-6 pb-20 z-10 focus:outline-hidden"
              >
                {children}
              </main>
            </div>
          </div>
        </AuthGuard>
      </QueryProvider>
    </ScopedIntlProvider>
  );
}
