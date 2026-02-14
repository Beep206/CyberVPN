'use client';

import { useEffect, useState } from 'react';
import { useAuthStore } from '@/stores/auth-store';

interface AuthProviderProps {
  children: React.ReactNode;
  /** Optional skeleton to show during hydration */
  skeleton?: React.ReactNode;
}

/**
 * AuthProvider handles session persistence on app load.
 * It checks for existing session by calling /auth/session on mount.
 * Handles hydration mismatch by deferring auth state to client.
 */
export function AuthProvider({ children, skeleton }: AuthProviderProps) {
  const [isHydrated, setIsHydrated] = useState(false);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  // Handle hydration
  /* eslint-disable react-hooks/set-state-in-effect -- Hydration guard pattern */
  useEffect(() => {
    setIsHydrated(true);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Check session on mount
  useEffect(() => {
    if (isHydrated) {
      // SEC-01: httpOnly cookies are source of truth and cannot be inspected
      // from JS, so always ask the backend for current session.
      fetchUser();
    }
  }, [isHydrated, fetchUser]);

  // Show skeleton until hydrated to prevent flash of unauthenticated state
  if (!isHydrated) {
    return skeleton ?? null;
  }

  return <>{children}</>;
}

/**
 * Hook to check if auth state is hydrated
 * Use this to prevent rendering auth-dependent UI until hydration is complete
 */
export function useAuthHydrated() {
  const [isHydrated, setIsHydrated] = useState(false);

  /* eslint-disable react-hooks/set-state-in-effect -- Auth cookie check on mount */
  useEffect(() => {
    setIsHydrated(true);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  return isHydrated;
}
