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
 * It checks for existing session by calling /auth/me on mount.
 * Handles hydration mismatch by deferring auth state to client.
 */
export function AuthProvider({ children, skeleton }: AuthProviderProps) {
  const [isHydrated, setIsHydrated] = useState(false);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  // Handle hydration
  useEffect(() => {
    setIsHydrated(true);
  }, []);

  // Check session on mount
  useEffect(() => {
    if (isHydrated) {
      // Only fetch if we think we might be authenticated (persisted state)
      // This prevents unnecessary API calls for new visitors
      const storedAuth = localStorage.getItem('auth-storage');
      if (storedAuth) {
        try {
          const parsed = JSON.parse(storedAuth);
          if (parsed.state?.isAuthenticated) {
            fetchUser();
          }
        } catch {
          // Invalid stored data, clear it
          localStorage.removeItem('auth-storage');
        }
      }
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

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  return isHydrated;
}
