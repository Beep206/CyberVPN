'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { usePathname, useRouter } from '@/i18n/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { useAuthStore } from '@/stores/auth-store';
import { stagePendingTwoFactorSession } from '@/features/auth/lib/pending-twofa-client';
import { getDefaultMiniAppPath } from '@/features/auth/lib/redirect-path';
import { isMiniAppRoute } from '@/features/auth/lib/session';
import { MINIAPP_AUTH_RESTORE_REQUIRED_EVENT } from '@/lib/api/client';
import { Loader2, AlertCircle, Shield } from 'lucide-react';
import { motion } from 'motion/react';

/**
 * TelegramMiniAppAuthProvider detects if running inside a Telegram Mini App
 * and auto-authenticates using initData. Shows loading state during auth,
 * falls back to standard login on error.
 */
export function TelegramMiniAppAuthProvider({
    children,
}: {
    children: React.ReactNode;
}) {
    const router = useRouter();
    const pathname = usePathname();
    const locale = useLocale();
    const t = useTranslations('Auth.telegram');
    const queryClient = useQueryClient();
    const { telegramMiniAppAuth, isAuthenticated, isMiniApp } = useAuthStore();
    const [runtimeIsMiniApp, setRuntimeIsMiniApp] = useState(false);
    const [telegramDetectionFinished, setTelegramDetectionFinished] = useState(false);
    const [authError, setAuthError] = useState<string | null>(null);
    const hasAttempted = useRef(false);
    const restoreInFlight = useRef(false);
    const effectiveIsMiniApp = isMiniApp || runtimeIsMiniApp;
    const isMiniAppRoutePath = isMiniAppRoute(pathname);
    const shouldGateMiniApp = effectiveIsMiniApp || isMiniAppRoutePath;

    useEffect(() => {
        let cancelled = false;
        let timeoutId: ReturnType<typeof setTimeout> | null = null;
        let attempts = 0;
        const maxAttempts = 80;

        const detectTelegramWebApp = () => {
            if (cancelled) return;

            const detected = typeof window !== 'undefined' && Boolean(window.Telegram?.WebApp?.initData);
            if (detected) {
                setRuntimeIsMiniApp(true);
                setTelegramDetectionFinished(true);
                return;
            }

            attempts += 1;
            if (attempts < maxAttempts) {
                timeoutId = setTimeout(detectTelegramWebApp, 250);
                return;
            }

            setTelegramDetectionFinished(true);
        };

        detectTelegramWebApp();

        return () => {
            cancelled = true;
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
        };
    }, []);

    const invalidateMiniAppQueries = useCallback(() => {
        void queryClient.invalidateQueries({
            predicate: (query) => {
                const [queryKey] = query.queryKey;
                return typeof queryKey === 'string' && queryKey.startsWith('miniapp-');
            },
        });
    }, [queryClient]);

    const authenticateMiniApp = useCallback(async () => {
        const miniAppHomePath = getDefaultMiniAppPath(locale);
        setAuthError(null);
        try {
            const result = await telegramMiniAppAuth();
            if (result.requires_2fa && result.tfa_token) {
                await stagePendingTwoFactorSession({
                    token: result.tfa_token,
                    locale,
                    returnTo: miniAppHomePath,
                    isNewUser: result.is_new_user,
                });
                router.push(`/login?2fa=true&redirect=${encodeURIComponent(miniAppHomePath)}`);
                return;
            }
            invalidateMiniAppQueries();
            router.push('/miniapp/home');
        } catch {
            setAuthError(t('miniAppAutoAuth'));
        }
    }, [invalidateMiniAppQueries, locale, router, telegramMiniAppAuth, t]);

    useEffect(() => {
        if (!effectiveIsMiniApp || isAuthenticated || hasAttempted.current) return;
        hasAttempted.current = true;
        const timeoutId = window.setTimeout(() => {
            void authenticateMiniApp();
        }, 0);
        return () => {
            window.clearTimeout(timeoutId);
        };
    }, [effectiveIsMiniApp, isAuthenticated, authenticateMiniApp]);

    useEffect(() => {
        if (!shouldGateMiniApp) return;

        const handleMiniAppAuthRestoreRequired = () => {
            if (restoreInFlight.current) return;
            if (typeof window === 'undefined' || !window.Telegram?.WebApp?.initData) {
                setAuthError(t('miniAppAutoAuth'));
                return;
            }

            restoreInFlight.current = true;
            hasAttempted.current = true;
            void authenticateMiniApp().finally(() => {
                restoreInFlight.current = false;
            });
        };

        window.addEventListener(MINIAPP_AUTH_RESTORE_REQUIRED_EVENT, handleMiniAppAuthRestoreRequired);
        return () => {
            window.removeEventListener(MINIAPP_AUTH_RESTORE_REQUIRED_EVENT, handleMiniAppAuthRestoreRequired);
        };
    }, [authenticateMiniApp, shouldGateMiniApp, t]);

    // Standard web routes keep the normal auth flow.
    if (!shouldGateMiniApp) {
        return <>{children}</>;
    }

    // Authenticated — render children
    if (isAuthenticated) {
        return <>{children}</>;
    }

    const routeAuthError = isMiniAppRoutePath && telegramDetectionFinished && !effectiveIsMiniApp
        ? t('miniAppAutoAuth')
        : authError;

    // Error state — keep Mini App routes gated to avoid exposing the web guest state.
    if (routeAuthError) {
        return (
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center gap-4 p-8 text-center"
            >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 border border-red-500/20">
                    <AlertCircle className="h-6 w-6 text-red-400" aria-hidden="true" />
                </div>
                <p className="text-sm text-muted-foreground font-mono" role="alert">
                    {routeAuthError}
                </p>
                {!isMiniAppRoutePath ? children : null}
            </motion.div>
        );
    }

    // Loading state
    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center gap-4 p-8 text-center"
        >
            <div className="relative">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-neon-cyan/10 border border-neon-cyan/20">
                    <Shield className="h-8 w-8 text-neon-cyan" aria-hidden="true" />
                </div>
                <Loader2 className="absolute -top-1 -right-1 h-6 w-6 text-neon-cyan animate-spin" aria-hidden="true" />
            </div>
            <p className="text-sm text-muted-foreground font-mono">
                {t('miniAppAutoAuth')}
            </p>
        </motion.div>
    );
}
