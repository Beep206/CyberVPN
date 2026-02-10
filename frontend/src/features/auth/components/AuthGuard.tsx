'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter, usePathname } from '@/i18n/navigation';
import { useAuthStore } from '@/stores/auth-store';
import { Loader2 } from 'lucide-react';

interface AuthGuardProps {
    children: React.ReactNode;
}

/**
 * Client-side auth guard that redirects to login if not authenticated.
 * SEC-01: Auth is via httpOnly cookies — always attempt /auth/me to check session.
 */
export function AuthGuard({ children }: AuthGuardProps) {
    const router = useRouter();
    const pathname = usePathname();
    const { isAuthenticated, isLoading, fetchUser } = useAuthStore();
    const [isChecking, setIsChecking] = useState(true);
    const fetchAttempted = useRef(false);

    useEffect(() => {
        const checkAuth = async () => {
            if (isAuthenticated) {
                setIsChecking(false);
                return;
            }

            // Guard against double-fetch (AuthProvider may have already called fetchUser)
            if (isLoading || fetchAttempted.current) {
                return;
            }

            fetchAttempted.current = true;

            // SEC-01: httpOnly cookies are invisible to JS — always try /auth/me
            try {
                await fetchUser();
            } catch {
                // Session invalid or expired — redirect will happen below
            }

            setIsChecking(false);
        };

        checkAuth();
    }, [isAuthenticated, isLoading, fetchUser]);

    useEffect(() => {
        if (!isChecking && !isLoading && !isAuthenticated) {
            const redirectUrl = `/login?redirect=${encodeURIComponent(pathname)}`;
            router.push(redirectUrl);
        }
    }, [isChecking, isLoading, isAuthenticated, pathname, router]);

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

    return <>{children}</>;
}
