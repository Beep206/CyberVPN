'use client';

import { useEffect, useRef, useState } from 'react';
import {
  CreditCard,
  Download,
  HelpCircle,
  Home,
  LayoutDashboard,
  Menu,
  Network,
  Sparkles,
  X,
} from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
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

interface PublicTerminalMobileMenuProps {
  links: PublicHeaderNavLink[];
  locale: string;
}

export function PublicTerminalMobileMenu({ links, locale }: PublicTerminalMobileMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (menuRef.current?.contains(event.target as Node)) {
        return;
      }

      setIsOpen(false);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  return (
    <div ref={menuRef} className="relative lg:hidden">
      <button
        type="button"
        aria-label={isOpen ? 'Close navigation menu' : 'Open navigation menu'}
        aria-expanded={isOpen}
        aria-controls="public-mobile-navigation"
        onClick={() => setIsOpen((current) => !current)}
        className={cn(
          'touch-target inline-flex items-center justify-center rounded-lg border px-3',
          'border-border/60 bg-card/70 text-foreground shadow-sm backdrop-blur transition-colors',
          'hover:border-neon-cyan/50 hover:bg-neon-cyan/10 hover:text-neon-cyan',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan/50',
          'dark:border-white/10 dark:bg-black/40',
        )}
      >
        {isOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
      </button>

      <AnimatePresence>
        {isOpen ? (
          <motion.nav
            id="public-mobile-navigation"
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.16 }}
            className={cn(
              'absolute left-0 top-[calc(100%+0.75rem)] z-50 w-[min(20rem,calc(100vw-2rem))] overflow-hidden rounded-xl border p-2 shadow-2xl',
              'border-border/70 bg-popover/98 text-popover-foreground backdrop-blur-xl',
              'dark:border-white/10 dark:bg-black/95',
            )}
          >
            <div className="grid gap-1">
              {links.map((link) => {
                const Icon = iconMap[link.icon];

                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    locale={locale}
                    onClick={() => setIsOpen(false)}
                    className={cn(
                      'flex min-h-11 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                      'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan/50',
                    )}
                  >
                    <Icon className="h-4 w-4 text-neon-cyan" />
                    <span>{link.label}</span>
                  </Link>
                );
              })}
            </div>
          </motion.nav>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
