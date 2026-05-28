'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { authAnalytics } from '@/lib/analytics';
import type { User } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth-store';
import {
  consumeOAuthResultCookie,
  shouldBootstrapAuthSession,
} from '@/features/auth/lib/session';

async function fetchOptionalSession(): Promise<User | null> {
  try {
    const response = await fetch('/api/auth/optional-session', {
      cache: 'no-store',
      credentials: 'include',
      headers: {
        accept: 'application/json',
      },
    });

    if (!response.ok) {
      return null;
    }

    const user = await response.json();
    return user && typeof user === 'object' ? user as User : null;
  } catch {
    return null;
  }
}

/**
 * Restores an authenticated session in the background without wrapping or
 * delaying the rest of the route tree.
 */
export function AuthSessionBootstrap() {
  const pathname = usePathname();

  useEffect(() => {
    if (!shouldBootstrapAuthSession(pathname)) {
      return;
    }

    let cancelled = false;

    void fetchOptionalSession().then((user) => {
      if (cancelled) {
        return;
      }

      if (user) {
        useAuthStore.setState({
          error: null,
          isAuthenticated: true,
          isLoading: false,
          user,
        });
        authAnalytics.sessionRestored(user.id);
      } else if (!useAuthStore.getState().isAuthenticated) {
        useAuthStore.setState({
          error: null,
          isAuthenticated: false,
          isLoading: false,
          user: null,
        });
      }

      const provider = consumeOAuthResultCookie();

      if (provider && user) {
        authAnalytics.oauthCallbackSuccess(user.id, provider);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [pathname]);

  return null;
}
