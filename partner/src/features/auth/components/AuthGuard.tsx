'use client';

import { useEffect, useState } from 'react';
import { useLocale } from 'next-intl';
import { useRouter, usePathname } from '@/i18n/navigation';
import { authApi } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth-store';
import { buildInternalLoginHref } from '@/features/auth/lib/session';
import {
    ACCESS_DENIED_ERROR_CODE,
    hasPartnerPortalAccess,
    isPartnerPortalUser,
} from '@/features/auth/lib/partner-access';
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
    const locale = useLocale();
    const [isChecking, setIsChecking] = useState(true);
    const [isAuthorized, setIsAuthorized] = useState(false);
    const [redirectTarget, setRedirectTarget] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;

        const checkAuth = async () => {
            // [DEV PANEL ONLY] Auth Bypass Interceptor
            if (process.env.NODE_ENV === 'development' && typeof document !== 'undefined') {
                const isBypassed = document.cookie.split(';').some((item) => item.trim().startsWith('DEV_BYPASS_AUTH=true'));
                if (isBypassed) {
                    const mockRole = (typeof localStorage !== 'undefined' ? localStorage.getItem('USER_ROLE') : 'user') || 'user';
                    if (!hasPartnerPortalAccess(mockRole)) {
                        useAuthStore.setState({
                            user: null,
                            isAuthenticated: false,
                            isLoading: false,
                            error: null,
                        });
                        setIsAuthorized(false);
                        setRedirectTarget(`/login?error=${ACCESS_DENIED_ERROR_CODE}`);
                        setIsChecking(false);
                        return;
                    }

                    useAuthStore.setState({
                        user: {
                            id: 'dev-bypass-id',
                            email: 'dev@cybervpn.local',
                            login: 'DevUser',
                            role: mockRole as 'viewer' | 'user' | 'admin' | 'super_admin',
                            is_active: true,
                            is_email_verified: true,
                            created_at: new Date().toISOString(),
                            auth_realm_key: 'partner',
                            audience: 'cybervpn:partner',
                            principal_type: 'partner_operator',
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

                if (!hasPartnerPortalAccess(data)) {
                    try {
                        await authApi.logout();
                    } catch {
                        // Best effort cleanup; the session might already be half-open.
                    }

                    useAuthStore.setState({
                        user: null,
                        isAuthenticated: false,
                        isLoading: false,
                        error: null,
                    });
                    setIsAuthorized(false);
                    setRedirectTarget(`/login?error=${ACCESS_DENIED_ERROR_CODE}`);
                    return;
                }

                useAuthStore.setState({
                    user: data,
                    isAuthenticated: true,
                    isLoading: false,
                    error: null,
                });
                setIsAuthorized(true);
                setRedirectTarget(null);
            } catch (error: unknown) {
                if (!isMounted) return;

                const currentState = useAuthStore.getState();

                useAuthStore.setState({
                    user: null,
                    isAuthenticated: false,
                    isLoading: false,
                });
                setIsAuthorized(false);
                setRedirectTarget(buildInternalLoginHref(pathname, locale));

                const status = (error as { response?: { status?: number } }).response?.status;
                if (status !== 401 && status !== 403) {
                    if (currentState.isAuthenticated && isPartnerPortalUser(currentState.user)) {
                        useAuthStore.setState({
                            user: currentState.user,
                            isAuthenticated: true,
                            isLoading: false,
                            error: null,
                        });
                        setIsAuthorized(true);
                        setRedirectTarget(null);
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
    }, [locale, pathname]);

    useEffect(() => {
        if (!isChecking && !isAuthorized && redirectTarget) {
                router.push(redirectTarget);
        }
    }, [isChecking, isAuthorized, redirectTarget, router]);

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
