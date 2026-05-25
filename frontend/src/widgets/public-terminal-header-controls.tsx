'use client';

import { Bell, CreditCard, Download, HelpCircle, Home, LayoutDashboard, Network, Sparkles } from 'lucide-react';
import { useLocale } from 'next-intl';
import { CurrencySelector } from '@/features/currency-selector';
import { UserMenu } from '@/features/header/user-menu';
import { LanguageSelector } from '@/features/language-selector';
import { ThemeToggle } from '@/features/theme-toggle';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth-store';
import type { PublicHeaderNavLink } from '@/widgets/public-terminal-header';

const iconMap: Record<PublicHeaderNavLink['icon'], typeof Home> = {
  dashboard: LayoutDashboard,
  download: Download,
  features: Sparkles,
  help: HelpCircle,
  home: Home,
  network: Network,
  pricing: CreditCard,
};

interface PublicTerminalHeaderControlsProps {
  downloadLabel: string;
  loginLabel: string;
  locale?: string;
  navLinks: PublicHeaderNavLink[];
  registerLabel: string;
}

export function PublicTerminalHeaderControls({
  downloadLabel,
  loginLabel,
  locale: providedLocale,
  navLinks,
  registerLabel,
}: PublicTerminalHeaderControlsProps) {
  const activeLocale = useLocale();
  const locale = providedLocale ?? activeLocale;
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return (
    <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
      <nav aria-label="Primary" className="hidden items-center gap-1 xl:flex">
        {navLinks
          .filter((link) => link.href !== '/' && link.href !== '/features')
          .map((link) => {
            const Icon = iconMap[link.icon];

            return (
              <Link
                key={link.href}
                href={link.href}
                locale={locale}
                className="touch-target inline-flex items-center gap-2 rounded-lg border border-transparent px-3 text-sm font-medium text-muted-foreground transition-all hover:border-border hover:bg-foreground/5 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 dark:hover:border-white/10 dark:hover:bg-white/5 dark:hover:text-white"
                data-seo-cta={link.icon}
                data-seo-zone="public_header_nav"
              >
                <Icon className="h-4 w-4" />
                <span>{link.label}</span>
              </Link>
            );
          })}
      </nav>

      <div className="mx-1 hidden h-6 w-px bg-grid-line/30 xl:block" />

      <div className="flex items-center gap-2">
        <ThemeToggle />
        <LanguageSelector />
        <CurrencySelector />
      </div>

      <div className="mx-1 hidden h-6 w-px bg-grid-line/30 lg:block" />

      <Link
        href="/download"
        locale={locale}
        className="touch-target hidden items-center gap-2 rounded-lg border border-grid-line/30 bg-terminal-surface/30 px-3 text-sm font-medium text-muted-foreground transition-all hover:border-neon-cyan/50 hover:bg-neon-cyan/10 hover:text-neon-cyan focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 lg:inline-flex xl:hidden"
        data-seo-cta="download"
        data-seo-zone="public_header"
      >
        <Download className="h-4 w-4" />
        {downloadLabel}
      </Link>

      <div className="mx-1 hidden h-6 w-px bg-grid-line/30 lg:block" />

      {isAuthenticated ? (
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Notifications are not available yet"
            disabled
            title="Notifications are not available yet"
            className="touch-target inline-flex items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-surface/30 px-3 text-muted-foreground opacity-60"
          >
            <Bell className="h-4 w-4" />
          </button>
          <UserMenu />
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <Link
            href="/login"
            locale={locale}
            className="touch-target hidden items-center justify-center whitespace-nowrap rounded-lg border border-transparent px-4 text-sm font-medium text-muted-foreground ring-offset-background transition-all hover:border-border hover:bg-foreground/5 hover:text-foreground dark:hover:border-white/10 dark:hover:bg-white/5 dark:hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 lg:inline-flex"
            data-seo-cta="login"
            data-seo-zone="public_header"
          >
            {loginLabel}
          </Link>
          <Link
            href="/register"
            locale={locale}
            className={cn(
              'touch-target inline-flex items-center justify-center whitespace-nowrap rounded-lg border border-neon-cyan/20 px-3 text-xs font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 sm:px-4 sm:text-sm',
              'bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan hover:text-black hover:shadow-[0_0_15px_rgba(0,255,255,0.3)]',
            )}
            data-seo-cta="register"
            data-seo-zone="public_header"
          >
            {registerLabel}
          </Link>
        </div>
      )}
    </div>
  );
}
