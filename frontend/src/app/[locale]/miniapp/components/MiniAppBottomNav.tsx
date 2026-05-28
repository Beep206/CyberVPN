'use client';

import { usePathname } from '@/i18n/navigation';
import { Link } from '@/i18n/navigation';
import {
  Gift,
  Home,
  CreditCard,
  Wallet,
  User,
  type LucideIcon,
} from 'lucide-react';
import { motion } from 'motion/react';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';
import { useTranslations } from 'next-intl';
import {
  isAnyGrowthSurfaceEnabled,
  useClientCapabilities,
} from '@/features/client-capabilities/useClientCapabilities';

interface NavItem {
  href: string;
  icon: LucideIcon;
  label: string;
  match: (path: string) => boolean;
}

export function MiniAppBottomNav() {
  const pathname = usePathname();
  const t = useTranslations('MiniApp.nav');
  const { hapticSelection } = useTelegramWebApp();
  const { data: capabilities } = useClientCapabilities();
  const growthVisible = isAnyGrowthSurfaceEnabled(capabilities);

  const navItems: NavItem[] = [
    {
      href: '/miniapp/home',
      icon: Home,
      label: t('home'),
      match: (path) =>
        path === '/miniapp/home' || path === '/miniapp' || path === '/miniapp/',
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
    ...(growthVisible
      ? [
          {
            href: '/miniapp/referral',
            icon: Gift,
            label: t('referral'),
            match: (path: string) => path.startsWith('/miniapp/referral'),
          },
        ]
      : []),
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

  return (
    <nav
      className="miniapp-nav fixed bottom-0 left-0 right-0 z-50 border-t backdrop-blur-xl"
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
