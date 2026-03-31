import Link from 'next/link';
import { ArrowLeft, Shield } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import { ScopedIntlProvider } from '@/app/providers/scoped-intl-provider';
import { AUTH_CLIENT_NAMESPACES } from '@/i18n/client-namespaces';
import { AuthSceneLoader } from '@/features/auth/components/AuthSceneLoader';
import { MiniAppNavGuard } from '@/features/auth/components/MiniAppNavGuard';
import { TelegramMiniAppAuthProvider } from '@/features/auth/components/TelegramMiniAppAuthProvider';
import { LanguageSelector } from '@/features/language-selector';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { ThemeToggle } from '@/features/theme-toggle';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Auth.meta' });

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

        <MiniAppNavGuard>
          <nav className="fixed top-0 left-0 right-0 z-20 flex items-center justify-between pt-[calc(var(--safe-area-top)+1rem)] pr-[calc(var(--mobile-page-gutter)+var(--safe-area-right))] pb-4 pl-[calc(var(--mobile-page-gutter)+var(--safe-area-left))] md:px-6 md:pb-6">
            <Link
              href="/"
              aria-label="Back to home"
              className="touch-target inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors font-mono text-sm group rounded-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
            >
              <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
              <span className="hidden sm:inline">back_to_home</span>
            </Link>

            <Link href="/" aria-label="CyberVPN home" className="touch-target absolute left-1/2 -translate-x-1/2 inline-flex items-center gap-2 group rounded-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]">
              <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 border border-neon-cyan/30 group-hover:border-neon-cyan/60 transition-colors">
                <Shield className="h-4 w-4 text-neon-cyan" />
              </div>
              <span className="font-display text-lg font-bold tracking-tight text-foreground hidden sm:inline">
                Cyber<span className="text-neon-cyan">VPN</span>
              </span>
            </Link>

            <div className="flex items-center gap-3">
              <ThemeToggle />
              <LanguageSelector />
            </div>
          </nav>
        </MiniAppNavGuard>

        <main id="main-content" tabIndex={-1} className="keyboard-safe-bottom relative z-10 w-full max-w-lg px-[calc(var(--mobile-page-gutter)+var(--safe-area-left))] pr-[calc(var(--mobile-page-gutter)+var(--safe-area-right))] pt-[calc(var(--safe-area-top)+5.5rem)] pb-[calc(var(--safe-area-bottom)+2rem)] focus:outline-hidden md:px-4 md:py-20">
          <TelegramMiniAppAuthProvider>{children}</TelegramMiniAppAuthProvider>
        </main>

        <div className="fixed bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neon-cyan/30 to-transparent z-20" />
      </div>
    </ScopedIntlProvider>
  );
}
