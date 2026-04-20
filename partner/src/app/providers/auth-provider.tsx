'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';
import { shouldBootstrapAuthSession } from '@/features/auth/lib/session';

/**
 * Restores an authenticated session in the background without wrapping or
 * delaying the rest of the route tree.
 */
export function AuthSessionBootstrap() {
  const pathname = usePathname();
  const fetchUser = useAuthStore((s) => s.fetchUser);

  useEffect(() => {
    if (!shouldBootstrapAuthSession(pathname)) {
      return;
    }

    void fetchUser();
  }, [fetchUser, pathname]);

  return null;
}
