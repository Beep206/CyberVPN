'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from '@/i18n/navigation';
import { authApi } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth-store';
import { buildLocalizedLoginRedirect } from '@/features/auth/lib/session';
import { Loader2 } from 'lucide-react';

interface AuthGuardProps {
    children: React.ReactNode;
}

/**
 * Client-side auth guard that validates session via backend cookies.
 *
 * The source of truth is /auth/me (httpOnly cookie auth), not persisted
 * client flags. This avoids race conditions between hydration and redirects.
 */
export function AuthGuard({ children }: AuthGuardProps) {
    const router = useRouter();
    const pathname = usePathname();
    const [isChecking, setIsChecking] = useState(true);
    const [isAuthorized, setIsAuthorized] = useState(false);

    useEffect(() => {
        let isMounted = true;

        const checkAuth = async () => {
            // [DEV PANEL ONLY] Auth Bypass Interceptor
            if (process.env.NODE_ENV === 'development' && typeof document !== 'undefined') {
                const isBypassed = document.cookie.split(';').some((item) => item.trim().startsWith('DEV_BYPASS_AUTH=true'));
                if (isBypassed) {
                    const mockRole = (typeof localStorage !== 'undefined' ? localStorage.getItem('USER_ROLE') : 'admin') || 'admin';
                    useAuthStore.setState({
                        user: {
                            id: 'dev-bypass-id',
                            email: 'dev@cybervpn.local',
                            login: 'DevUser',
                            role: mockRole as 'viewer' | 'user' | 'admin' | 'super_admin',
                            is_active: true,
                            is_email_verified: true,
                            created_at: new Date().toISOString()
                        },
                        isAuthenticated: true,
                        isLoading: false,
                        error: null,
                    });
                    setIsAuthorized(true);
                    setIsChecking(false);
                    return;
                }
            }

            try {
                const { data } = await authApi.session();
                if (!isMounted) return;

                useAuthStore.setState({
                    user: data,
                    isAuthenticated: true,
                    isLoading: false,
                    error: null,
                });
                setIsAuthorized(true);
            } catch (error: unknown) {
                if (!isMounted) return;

                const currentState = useAuthStore.getState();

                useAuthStore.setState({
                    user: null,
                    isAuthenticated: false,
                    isLoading: false,
                });
                setIsAuthorized(false);

                const status = (error as { response?: { status?: number } }).response?.status;
                if (status !== 401 && status !== 403) {
                    if (currentState.isAuthenticated && currentState.user) {
                        useAuthStore.setState({
                            user: currentState.user,
                            isAuthenticated: true,
                            isLoading: false,
                            error: null,
                        });
                        setIsAuthorized(true);
                    }
                }
            } finally {
                if (isMounted) {
                    setIsChecking(false);
                }
            }
        };

        checkAuth();

        return () => {
            isMounted = false;
        };
    }, []);

    useEffect(() => {
        if (!isChecking && !isAuthorized) {
                router.push(buildLocalizedLoginRedirect(pathname));
        }
    }, [isChecking, isAuthorized, pathname, router]);

    if (isChecking) {
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

    if (!isAuthorized) {
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
