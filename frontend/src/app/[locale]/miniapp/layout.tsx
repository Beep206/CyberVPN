import { TelegramMiniAppAuthProvider } from '@/features/auth/components/TelegramMiniAppAuthProvider';
import { MiniAppBottomNav } from './components/MiniAppBottomNav';
import { ErrorBoundary } from '@/shared/ui/error-boundary';
import { getTranslations } from 'next-intl/server';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'MiniApp.meta' });

  return {
    title: t('title'),
    description: t('description'),
  };
}

export default function MiniAppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <TelegramMiniAppAuthProvider>
      <div className="flex flex-col min-h-screen w-full bg-background text-foreground">
        {/* Skip to main content link for accessibility */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:bg-neon-cyan focus:text-black focus:px-4 focus:py-2 focus:rounded-sm focus:font-mono focus:text-sm"
        >
          Skip to main content
        </a>

        {/* Main content - with bottom padding for nav bar */}
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

        {/* Bottom Navigation */}
        <ErrorBoundary label="Bottom Navigation">
          <MiniAppBottomNav />
        </ErrorBoundary>
      </div>
    </TelegramMiniAppAuthProvider>
  );
}
