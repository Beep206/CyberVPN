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
  }, {
    locale,
    routeType: 'private',
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

          <div className="flex min-h-dvh w-full bg-terminal-bg text-foreground">
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

            <div className="relative flex min-h-dvh flex-1 flex-col md:pl-64">
              <ErrorBoundary label="Header">
                <TerminalHeader performanceMode="always" showMobileSidebar />
              </ErrorBoundary>

              <main
                id="main-content"
                tabIndex={-1}
                aria-live="polite"
                className="relative z-10 flex-1 p-4 pb-20 focus:outline-hidden md:p-6"
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
