'use client';

import { usePathname } from '@/i18n/navigation';
import { Link } from '@/i18n/navigation';
import { Home, CreditCard, Wallet, User } from 'lucide-react';
import { motion } from 'motion/react';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';
import { useTranslations } from 'next-intl';

interface NavItem {
  href: string;
  icon: typeof Home;
  label: string;
  match: (path: string) => boolean;
}

export function MiniAppBottomNav() {
  const pathname = usePathname();
  const t = useTranslations('MiniApp.nav');
  const { hapticSelection, colorScheme } = useTelegramWebApp();

  const navItems: NavItem[] = [
    {
      href: '/miniapp/home',
      icon: Home,
      label: t('home'),
      match: (path) => path === '/miniapp/home' || path === '/miniapp' || path === '/miniapp/',
    },
    {
      href: '/miniapp/plans',
      icon: CreditCard,
      label: t('plans'),
      match: (path) => path.startsWith('/miniapp/plans'),
    },
    {
      href: '/miniapp/wallet',
      icon: Wallet,
      label: t('wallet'),
      match: (path) => path.startsWith('/miniapp/wallet'),
    },
    {
      href: '/miniapp/profile',
      icon: User,
      label: t('profile'),
      match: (path) => path.startsWith('/miniapp/profile'),
    },
  ];

  const handleNavClick = () => {
    hapticSelection();
  };

  // Use Telegram theme colors or fallback to cyberpunk
  const bgColor = colorScheme === 'dark'
    ? 'bg-[var(--tg-bg-color,oklch(0.05_0.015_260))]'
    : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';

  const borderColor = colorScheme === 'dark'
    ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]'
    : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

  return (
    <nav
      className={`fixed bottom-0 left-0 right-0 z-50 ${bgColor} border-t ${borderColor} backdrop-blur-xl`}
      role="navigation"
      aria-label={t('bottomNav')}
    >
      <div className="flex items-center justify-around h-16 max-w-screen-sm mx-auto px-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.match(pathname);

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={handleNavClick}
              className="relative flex flex-col items-center justify-center gap-1 px-3 py-2 min-w-[64px] touch-manipulation"
              aria-label={item.label}
              aria-current={isActive ? 'page' : undefined}
            >
              <div className="relative">
                <Icon
                  className={`h-6 w-6 transition-colors duration-200 ${
                    isActive
                      ? 'text-[var(--tg-link-color,var(--color-neon-cyan))]'
                      : 'text-[var(--tg-hint-color,var(--muted-foreground))]'
                  }`}
                  aria-hidden="true"
                />
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute -inset-2 rounded-lg bg-[var(--tg-link-color,var(--color-neon-cyan))]/10"
                    style={{ zIndex: -1 }}
                    transition={{
                      type: 'spring',
                      stiffness: 500,
                      damping: 30,
                    }}
                  />
                )}
              </div>
              <span
                className={`text-xs font-mono transition-colors duration-200 ${
                  isActive
                    ? 'text-[var(--tg-link-color,var(--color-neon-cyan))] font-semibold'
                    : 'text-[var(--tg-hint-color,var(--muted-foreground))]'
                }`}
              >
                {item.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
