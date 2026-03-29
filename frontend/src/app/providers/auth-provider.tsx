'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';

const TELEGRAM_LINK_ROUTE_RE = /^\/(?:[a-z]{2,3}-[A-Z]{2}\/)?telegram-link(?:\/|$)/;

/**
 * Restores an authenticated session in the background without wrapping or
 * delaying the rest of the route tree.
 */
export function AuthSessionBootstrap() {
  const pathname = usePathname();
  const fetchUser = useAuthStore((s) => s.fetchUser);

  useEffect(() => {
    if (!TELEGRAM_LINK_ROUTE_RE.test(pathname)) {
      void fetchUser();
    }
  }, [fetchUser, pathname]);

  return null;
}
