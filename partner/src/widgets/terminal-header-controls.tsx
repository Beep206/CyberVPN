'use client';

import { LanguageSelector } from '@/features/language-selector';
import { UserMenu } from '@/features/header/user-menu';
import { ThemeToggle } from '@/features/theme-toggle';
import { useAuthStore } from '@/stores/auth-store';

export function TerminalHeaderControls() {
  const { isAuthenticated, isLoading } = useAuthStore();

  return (
    <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <LanguageSelector />
      </div>

      <div className="mx-1 hidden h-6 w-px bg-grid-line/30 lg:block" />

      {isLoading ? (
        <div className="touch-target h-11 w-20 animate-pulse rounded-lg bg-muted/20 sm:w-24" />
      ) : isAuthenticated ? (
        <UserMenu />
      ) : null}
    </div>
  );
}
