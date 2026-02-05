'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from '@/i18n/navigation';
import { useAuthStore } from '@/stores/auth-store';
import { tokenStorage } from '@/lib/api/client';
import { Loader2 } from 'lucide-react';

interface AuthGuardProps {
    children: React.ReactNode;
}

/**
 * Client-side auth guard that redirects to login if not authenticated.
 * Checks localStorage for tokens and validates with the server.
 */
export function AuthGuard({ children }: AuthGuardProps) {
    const router = useRouter();
    const pathname = usePathname();
    const { isAuthenticated, isLoading, fetchUser } = useAuthStore();
    const [isChecking, setIsChecking] = useState(true);

    useEffect(() => {
        const checkAuth = async () => {
            // If already authenticated in store, we're good
            if (isAuthenticated) {
                setIsChecking(false);
                return;
            }

            // Check if we have tokens in localStorage
            if (!tokenStorage.hasTokens()) {
                // No tokens - not authenticated
                setIsChecking(false);
                return;
            }

            // We have tokens but store says not authenticated
            // Try to restore session by fetching user
            try {
                await fetchUser();
            } catch {
                // Failed to restore session - tokens might be expired
                tokenStorage.clearTokens();
            }

            setIsChecking(false);
        };

        checkAuth();
    }, [isAuthenticated, fetchUser]);

    useEffect(() => {
        // After checking, if not authenticated, redirect to login
        if (!isChecking && !isLoading && !isAuthenticated) {
            const redirectUrl = `/login?redirect=${encodeURIComponent(pathname)}`;
            router.push(redirectUrl);
        }
    }, [isChecking, isLoading, isAuthenticated, pathname, router]);

    // Show loading while checking auth
    if (isChecking || isLoading) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-terminal-bg">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-8 w-8 animate-spin text-neon-cyan" />
                    <p className="font-mono text-sm text-muted-foreground">
                        AUTHENTICATING...
                    </p>
                </div>
            </div>
        );
    }

    // Not authenticated - will redirect
    if (!isAuthenticated) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-terminal-bg">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-8 w-8 animate-spin text-neon-cyan" />
                    <p className="font-mono text-sm text-muted-foreground">
                        REDIRECTING TO LOGIN...
                    </p>
                </div>
            </div>
        );
    }

    // Authenticated - render children
    return <>{children}</>;
}
