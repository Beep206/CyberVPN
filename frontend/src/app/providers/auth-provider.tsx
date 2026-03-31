'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { authAnalytics } from '@/lib/analytics';
import { useAuthStore } from '@/stores/auth-store';
import {
  consumeOAuthResultCookie,
  shouldBootstrapAuthSession,
} from '@/features/auth/lib/session';

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

    void fetchUser().then(() => {
      const provider = consumeOAuthResultCookie();
      const currentUser = useAuthStore.getState().user;

      if (provider && currentUser) {
        authAnalytics.oauthCallbackSuccess(currentUser.id, provider);
      }
    });
  }, [fetchUser, pathname]);

  return null;
}
