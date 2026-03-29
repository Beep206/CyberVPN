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
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <LanguageSelector />
      </div>

      <div className="h-6 w-px bg-grid-line/30 mx-2" />

      <QRCodeDropdown />

      <div className="h-6 w-px bg-grid-line/30 mx-2" />

      {mounted ? (
        isLoading ? (
          <div className="h-9 w-24 bg-muted/20 animate-pulse rounded-lg" />
        ) : isAuthenticated ? (
          <div className="flex items-center gap-3">
            <UserMenu />
            <NotificationDropdown />
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link
              href="/login"
              className="hidden sm:inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-white/5 hover:text-white h-9 px-4 text-muted-foreground border border-transparent hover:border-white/10"
            >
              {loginLabel}
            </Link>
            <Link
              href="/register"
              className={cn(
                'inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
                'bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan hover:text-black border border-neon-cyan/20 h-9 px-4 hover:shadow-[0_0_15px_rgba(0,255,255,0.3)]',
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
