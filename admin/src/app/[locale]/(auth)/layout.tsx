import { Shield } from 'lucide-react';
import { ScopedIntlProvider } from '@/app/providers/scoped-intl-provider';
import { AUTH_CLIENT_NAMESPACES } from '@/i18n/client-namespaces';
import { getCachedTranslations } from '@/i18n/server';
import { AuthSceneLoader } from '@/features/auth/components/AuthSceneLoader';
import { LanguageSelector } from '@/features/language-selector';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { ThemeToggle } from '@/features/theme-toggle';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Auth.meta');

  return withSiteMetadata({
    title: t('title'),
    description: t('description'),
  }, {
    locale,
    routeType: 'private',
  });
}

export default async function AuthLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  return (
    <ScopedIntlProvider locale={locale} namespaces={AUTH_CLIENT_NAMESPACES}>
      <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-terminal-bg">
        <AuthSceneLoader />
        <div className="absolute inset-0 bg-terminal-bg/70 dark:bg-terminal-bg/50 z-[1]" />
        <div className="absolute top-1/3 left-1/4 w-96 h-96 bg-neon-cyan/10 dark:bg-neon-cyan/20 rounded-full blur-[120px] z-[1] pointer-events-none" />
        <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-neon-purple/10 dark:bg-neon-purple/20 rounded-full blur-[120px] z-[1] pointer-events-none" />

        <nav className="fixed top-0 left-0 right-0 z-20 flex items-center justify-between pt-[calc(var(--safe-area-top)+1rem)] pr-[calc(var(--mobile-page-gutter)+var(--safe-area-right))] pb-4 pl-[calc(var(--mobile-page-gutter)+var(--safe-area-left))] md:px-6 md:pb-6">
          <div
            aria-label="Ozoxy admin"
            className="inline-flex items-center gap-3 rounded-lg border border-neon-cyan/20 bg-terminal-surface/30 px-3 py-2 backdrop-blur-sm"
          >
            <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 border border-neon-cyan/30">
              <Shield className="h-4 w-4 text-neon-cyan" />
            </div>
            <div className="flex flex-col leading-none">
              <span className="font-display text-sm font-bold tracking-[0.18em] text-foreground uppercase">
                Ozoxy Admin
              </span>
              <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                secure access node
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <LanguageSelector />
          </div>
        </nav>

        <main id="main-content" tabIndex={-1} className="keyboard-safe-bottom relative z-10 w-full max-w-lg px-[calc(var(--mobile-page-gutter)+var(--safe-area-left))] pr-[calc(var(--mobile-page-gutter)+var(--safe-area-right))] pt-[calc(var(--safe-area-top)+5.5rem)] pb-[calc(var(--safe-area-bottom)+2rem)] focus:outline-hidden md:px-4 md:py-20">
          {children}
        </main>

        <div className="fixed bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neon-cyan/30 to-transparent z-20" />
      </div>
    </ScopedIntlProvider>
  );
}
