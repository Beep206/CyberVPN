import { getTranslations } from 'next-intl/server';
import { QueryProvider } from '@/app/providers/query-provider';
import { ScopedIntlProvider } from '@/app/providers/scoped-intl-provider';
import { MINI_APP_CLIENT_NAMESPACES } from '@/i18n/client-namespaces';
import { TelegramMiniAppAuthProvider } from '@/features/auth/components/TelegramMiniAppAuthProvider';
import { ErrorBoundary } from '@/shared/ui/error-boundary';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { MiniAppBottomNav } from './components/MiniAppBottomNav';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'MiniApp.meta' });

  return withSiteMetadata({
    title: t('title'),
    description: t('description'),
  });
}

export default async function MiniAppLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  return (
    <ScopedIntlProvider locale={locale} namespaces={MINI_APP_CLIENT_NAMESPACES}>
      <QueryProvider>
        <TelegramMiniAppAuthProvider>
          <div className="flex flex-col min-h-screen w-full bg-background text-foreground">
            <a
              href="#main-content"
              className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:bg-neon-cyan focus:text-black focus:px-4 focus:py-2 focus:rounded-sm focus:font-mono focus:text-sm"
            >
              Skip to main content
            </a>

            <ErrorBoundary label="Mini App Content">
              <main
                id="main-content"
                tabIndex={-1}
                className="flex-1 overflow-y-auto overflow-x-hidden p-4 pb-20"
                aria-live="polite"
              >
                {children}
              </main>
            </ErrorBoundary>

            <ErrorBoundary label="Bottom Navigation">
              <MiniAppBottomNav />
            </ErrorBoundary>
          </div>
        </TelegramMiniAppAuthProvider>
      </QueryProvider>
    </ScopedIntlProvider>
  );
}
