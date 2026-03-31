'use client';

import Link from 'next/link';
import { useSyncExternalStore } from 'react';
import { LanguageSelector } from '@/features/language-selector';
import { QRCodeDropdown } from '@/features/header/qr-code-dropdown';
import { UserMenu } from '@/features/header/user-menu';
import { NotificationDropdown } from '@/features/notifications/notification-dropdown';
import { ThemeToggle } from '@/features/theme-toggle';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth-store';

interface TerminalHeaderControlsProps {
  loginLabel: string;
  registerLabel: string;
}

export function TerminalHeaderControls({
  loginLabel,
  registerLabel,
}: TerminalHeaderControlsProps) {
  const { isAuthenticated, isLoading } = useAuthStore();
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

  return (
    <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <LanguageSelector />
      </div>

      <div className="mx-1 hidden h-6 w-px bg-grid-line/30 lg:block" />

      <div className="hidden lg:block">
        <QRCodeDropdown />
      </div>

      <div className="mx-1 hidden h-6 w-px bg-grid-line/30 lg:block" />

      {mounted ? (
        isLoading ? (
          <div className="touch-target h-11 w-20 animate-pulse rounded-lg bg-muted/20 sm:w-24" />
        ) : isAuthenticated ? (
          <div className="flex items-center gap-2 sm:gap-3">
            <UserMenu />
            <div className="hidden sm:block">
              <NotificationDropdown />
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link
              href="/login"
              className="touch-target hidden items-center justify-center whitespace-nowrap rounded-lg border border-transparent px-4 text-sm font-medium text-muted-foreground ring-offset-background transition-all hover:border-white/10 hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 lg:inline-flex"
            >
              {loginLabel}
            </Link>
            <Link
              href="/register"
              className={cn(
                'touch-target inline-flex items-center justify-center whitespace-nowrap rounded-lg border border-neon-cyan/20 px-3 text-xs font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 sm:px-4 sm:text-sm',
                'bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan hover:text-black hover:shadow-[0_0_15px_rgba(0,255,255,0.3)]',
              )}
            >
              {registerLabel}
            </Link>
          </div>
        )
      ) : null}
    </div>
  );
}
