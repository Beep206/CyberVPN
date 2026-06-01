'use client';

import { usePathname } from '@/i18n/navigation';
import { Link } from '@/i18n/navigation';
import { motion } from 'motion/react';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';
import { useTranslations } from 'next-intl';
import { useClientCapabilities } from '@/features/client-capabilities/useClientCapabilities';
import { getMiniAppBottomNavItems } from '@/shared/cabinet-navigation';

export function MiniAppBottomNav() {
  const pathname = usePathname();
  const t = useTranslations('MiniApp');
  const { hapticSelection } = useTelegramWebApp();
  const { data: capabilities } = useClientCapabilities();
  const navItems = getMiniAppBottomNavItems({ capabilities });

  const handleNavClick = () => {
    hapticSelection();
  };

  return (
    <nav
      className="miniapp-nav fixed bottom-0 left-0 right-0 z-50 border-t backdrop-blur-xl"
      role="navigation"
      aria-label={t('nav.bottomNav')}
    >
      <div className="flex items-center justify-around h-16 max-w-screen-sm mx-auto px-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.match(pathname);
          const label = t(item.labelKey);

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={handleNavClick}
              className="relative flex flex-col items-center justify-center gap-1 px-3 py-2 min-w-[64px] touch-manipulation"
              aria-label={label}
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
                {label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
