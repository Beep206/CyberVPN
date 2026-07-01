'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { usePathname, useRouter } from '@/i18n/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { useAuthStore } from '@/stores/auth-store';
import { isMiniAppRoute } from '@/features/auth/lib/session';
import { MINIAPP_AUTH_RESTORE_RECOVERED_EVENT, MINIAPP_AUTH_RESTORE_REQUIRED_EVENT } from '@/lib/api/client';
import { customerOnboardingApi, type CustomerOnboardingCurrentResponse } from '@/features/customer-onboarding/api';
import {
    getPostAuthDestination,
    getPostRegistrationOnboardingPath,
    shouldRouteToPostRegistrationOnboarding,
} from '@/features/customer-onboarding/routing';
import { installMiniAppClientErrorListeners, reportMiniAppClientError } from '@/features/miniapp-runtime/lib/client-error-telemetry';
import { replaceMiniAppPath } from '@/features/miniapp-runtime/lib/navigation';
import { Loader2, AlertCircle, Shield, RotateCcw, Send, X } from 'lucide-react';
import { motion } from 'motion/react';

function getMiniAppReturnPath(pathname: string | null | undefined) {
    if (!pathname || pathname === '/miniapp' || pathname === '/miniapp/') {
        return '/miniapp/home';
    }

    return isMiniAppRoute(pathname) ? pathname : '/miniapp/home';
}

function isMiniAppPublicDiagnosticPath(pathname: string | null | undefined) {
    return Boolean(pathname && /^\/miniapp\/(?:health|diagnostics)(?:\/|$)/.test(pathname));
}

function isMiniAppOnboardingPath(pathname: string | null | undefined) {
    return Boolean(pathname && /^\/miniapp\/onboarding(?:\/|$)/.test(pathname));
}

function getTelegramBotUrl() {
    const username = (
        process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
        ?? process.env.NEXT_PUBLIC_TELEGRAM_BOT_NAME
        ?? 'CyberVPNBot'
    ).replace(/^@/, '');

    return `https://t.me/${username}`;
}

function fingerprintTelegramInitData(initData: string): string {
    let hash = 2166136261;
    for (let index = 0; index < initData.length; index += 1) {
        hash ^= initData.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
    }
    return `${initData.length}:${(hash >>> 0).toString(16)}`;
}

function getMiniAppAuthErrorCode(error: unknown): string | null {
    const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
    if (typeof detail !== 'object' || detail === null) {
        return null;
    }
    const code = (detail as { code?: unknown }).code;
    return typeof code === 'string' && code.trim() ? code.trim() : null;
}

function getMiniAppAuthErrorMessage(error: unknown, fallback: string) {
    const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
        return detail;
    }
    if (typeof detail === 'object' && detail !== null) {
        const record = detail as { message?: unknown; code?: unknown };
        if (typeof record.message === 'string' && record.message.trim()) {
            return record.message;
        }
        if (typeof record.code === 'string' && record.code.trim()) {
            return record.code;
        }
    }
    if (error instanceof Error && error.message.trim()) {
        return error.message;
    }
    return fallback;
}

type MiniAppOnboardingLookupResult =
    | { status: 'resolved'; onboarding: CustomerOnboardingCurrentResponse }
    | { status: 'failed' };

/**
 * TelegramMiniAppAuthProvider detects if running inside a Telegram Mini App
 * and auto-authenticates using a session-first restore, then initData when needed.
 * Mini App routes stay inside the Telegram recovery flow on auth errors.
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
    const { telegramMiniAppAuth, fetchUser, isAuthenticated, isMiniApp } = useAuthStore();
    const [runtimeIsMiniApp, setRuntimeIsMiniApp] = useState(false);
    const [telegramDetectionFinished, setTelegramDetectionFinished] = useState(false);
    const [authError, setAuthError] = useState<string | null>(null);
    const [onboardingGatePending, setOnboardingGatePending] = useState(false);
    const [onboardingGateCheckedPath, setOnboardingGateCheckedPath] = useState<string | null>(null);
    const hasAttempted = useRef(false);
    const restoreInFlight = useRef(false);
    const authInFlight = useRef<Promise<void> | null>(null);
    const spentInitDataFingerprints = useRef<Set<string>>(new Set());
    const onboardingGateInFlight = useRef<{ path: string | null; promise: Promise<void> } | null>(null);
    const onboardingGateRequestId = useRef(0);
    const effectiveIsMiniApp = isMiniApp || runtimeIsMiniApp;
    const isMiniAppRoutePath = isMiniAppRoute(pathname);
    const shouldGateMiniApp = isMiniAppRoutePath && !isMiniAppPublicDiagnosticPath(pathname);
    const shouldCheckMiniAppOnboarding = (
        shouldGateMiniApp
        && isAuthenticated
        && isMiniAppRoutePath
        && !isMiniAppOnboardingPath(pathname)
    );
    const shouldHoldMiniAppContent = (
        shouldCheckMiniAppOnboarding
        && (onboardingGatePending || onboardingGateCheckedPath !== pathname || authError !== null)
    );

    useEffect(() => {
        if (!isMiniAppRoutePath) return undefined;
        return installMiniAppClientErrorListeners();
    }, [isMiniAppRoutePath]);

    useEffect(() => {
        let cancelled = false;
        let timeoutId: ReturnType<typeof setTimeout> | null = null;
        let attempts = 0;
        const maxAttempts = 80;

        const detectTelegramWebApp = () => {
            if (cancelled) return;

            const detected = typeof window !== 'undefined' && Boolean(window.Telegram?.WebApp);
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

    const refreshMiniAppQueriesAfterAuthRecovery = useCallback(async () => {
        await queryClient.resetQueries({
            predicate: (query) => {
                const [queryKey] = query.queryKey;
                return typeof queryKey === 'string' && queryKey.startsWith('miniapp-');
            },
        });
    }, [queryClient]);

    const resolveMiniAppOnboardingFromCurrentState = useCallback(async (): Promise<MiniAppOnboardingLookupResult> => {
        try {
            const { data } = await customerOnboardingApi.current();
            return { status: 'resolved', onboarding: data };
        } catch (error) {
            reportMiniAppClientError({
                eventType: 'miniapp_onboarding_gate_failed',
                errorName: error instanceof Error ? error.name : 'MiniAppOnboardingGateError',
                errorMessage: getMiniAppAuthErrorMessage(error, 'Mini App onboarding gate failed'),
                chunk: null,
            });
            return { status: 'failed' };
        }
    }, []);

    const routeMiniAppOnboardingIfNeeded = useCallback(async () => {
        const isCurrentSessionAuthenticated = useAuthStore.getState().isAuthenticated;
        if (
            !isCurrentSessionAuthenticated
            || !shouldGateMiniApp
            || !isMiniAppRoutePath
            || isMiniAppOnboardingPath(pathname)
            || isMiniAppPublicDiagnosticPath(pathname)
        ) {
            setOnboardingGatePending(false);
            return;
        }
        const currentPath = pathname ?? null;
        if (onboardingGateInFlight.current?.path === currentPath) {
            await onboardingGateInFlight.current.promise;
            return;
        }

        const gateRequestId = onboardingGateRequestId.current + 1;
        onboardingGateRequestId.current = gateRequestId;
        const gateAttempt = (async () => {
            setOnboardingGatePending(true);
            setAuthError(null);
            const lookup = await resolveMiniAppOnboardingFromCurrentState();
            if (
                onboardingGateRequestId.current !== gateRequestId
                ||
                onboardingGateInFlight.current?.path !== currentPath
            ) {
                return;
            }

            if (lookup.status === 'failed') {
                setOnboardingGateCheckedPath(null);
                setOnboardingGatePending(false);
                setAuthError(t('miniAppAuthFailedMessage'));
                return;
            }

            if (shouldRouteToPostRegistrationOnboarding(lookup.onboarding)) {
                replaceMiniAppPath(router, getPostRegistrationOnboardingPath('miniapp'), locale);
                return;
            }
            setOnboardingGateCheckedPath(currentPath);
            setOnboardingGatePending(false);
        })();

        onboardingGateInFlight.current = { path: currentPath, promise: gateAttempt };
        try {
            await gateAttempt;
        } finally {
            if (onboardingGateRequestId.current === gateRequestId) {
                onboardingGateInFlight.current = null;
            }
        }
    }, [isMiniAppRoutePath, locale, pathname, resolveMiniAppOnboardingFromCurrentState, router, shouldGateMiniApp, t]);

    const restoreMiniAppSession = useCallback(async () => {
        await fetchUser();
        if (useAuthStore.getState().isAuthenticated) {
            setAuthError(null);
            await refreshMiniAppQueriesAfterAuthRecovery();
            await routeMiniAppOnboardingIfNeeded();
            return true;
        }
        return false;
    }, [fetchUser, refreshMiniAppQueriesAfterAuthRecovery, routeMiniAppOnboardingIfNeeded]);

    const authenticateMiniApp = useCallback(async () => {
        if (authInFlight.current) {
            await authInFlight.current;
            return;
        }

        const authAttempt = (async () => {
            const miniAppReturnPath = getMiniAppReturnPath(pathname);
            setAuthError(null);
            if (await restoreMiniAppSession()) {
                return;
            }
            if (typeof window === 'undefined' || !window.Telegram?.WebApp?.initData) {
                setAuthError(t('miniAppRequiredMessage'));
                return;
            }

            const initDataFingerprint = fingerprintTelegramInitData(window.Telegram.WebApp.initData);
            if (spentInitDataFingerprints.current.has(initDataFingerprint)) {
                if (await restoreMiniAppSession()) {
                    return;
                }
                setAuthError(t('miniAppAuthFailedMessage'));
                return;
            }

            try {
                const result = await telegramMiniAppAuth();
                spentInitDataFingerprints.current.add(initDataFingerprint);
                if (result.requires_2fa) {
                    setAuthError(t('miniAppTwoFactorUnsupported'));
                    return;
                }
                await refreshMiniAppQueriesAfterAuthRecovery();
                let onboarding = result.onboarding ?? null;
                if (onboarding === null) {
                    const lookup = await resolveMiniAppOnboardingFromCurrentState();
                    if (lookup.status === 'failed') {
                        setAuthError(t('miniAppAuthFailedMessage'));
                        return;
                    }
                    onboarding = lookup.onboarding;
                }
                const postAuthDestination = getPostAuthDestination({
                    onboarding,
                    surface: 'miniapp',
                });
                replaceMiniAppPath(
                    router,
                    postAuthDestination === '/miniapp/home' ? miniAppReturnPath : postAuthDestination,
                    locale,
                );
            } catch (error) {
                if (getMiniAppAuthErrorCode(error) === 'TELEGRAM_INIT_DATA_REPLAYED') {
                    spentInitDataFingerprints.current.add(initDataFingerprint);
                }
                if (await restoreMiniAppSession()) {
                    return;
                }
                setAuthError(getMiniAppAuthErrorMessage(error, t('miniAppAuthFailedMessage')));
                reportMiniAppClientError({
                    eventType: 'miniapp_auth_failed',
                    errorName: error instanceof Error ? error.name : 'MiniAppAuthError',
                    errorMessage: getMiniAppAuthErrorMessage(error, t('miniAppAuthFailedMessage')),
                    chunk: null,
                });
            }
        })();

        authInFlight.current = authAttempt;
        try {
            await authAttempt;
        } finally {
            if (authInFlight.current === authAttempt) {
                authInFlight.current = null;
            }
        }
    }, [
        locale,
        pathname,
        refreshMiniAppQueriesAfterAuthRecovery,
        resolveMiniAppOnboardingFromCurrentState,
        restoreMiniAppSession,
        router,
        telegramMiniAppAuth,
        t,
    ]);

    useEffect(() => {
        if (!shouldGateMiniApp || !effectiveIsMiniApp || isAuthenticated || hasAttempted.current) return;
        hasAttempted.current = true;
        void authenticateMiniApp();
    }, [shouldGateMiniApp, effectiveIsMiniApp, isAuthenticated, authenticateMiniApp]);

    useEffect(() => {
        if (!shouldCheckMiniAppOnboarding) {
            setOnboardingGatePending(false);
            return;
        }
        void routeMiniAppOnboardingIfNeeded();
    }, [routeMiniAppOnboardingIfNeeded, shouldCheckMiniAppOnboarding]);

    useEffect(() => {
        if (!shouldGateMiniApp) return;

        const handleMiniAppAuthRestoreRequired = () => {
            if (restoreInFlight.current) return;

            restoreInFlight.current = true;
            hasAttempted.current = true;
            void (async () => {
                if (await restoreMiniAppSession()) {
                    return;
                }
                await authenticateMiniApp();
            })().finally(() => {
                restoreInFlight.current = false;
            });
        };

        window.addEventListener(MINIAPP_AUTH_RESTORE_REQUIRED_EVENT, handleMiniAppAuthRestoreRequired);
        window.addEventListener(MINIAPP_AUTH_RESTORE_RECOVERED_EVENT, handleMiniAppAuthRestoreRequired);
        return () => {
            window.removeEventListener(MINIAPP_AUTH_RESTORE_REQUIRED_EVENT, handleMiniAppAuthRestoreRequired);
            window.removeEventListener(MINIAPP_AUTH_RESTORE_RECOVERED_EVENT, handleMiniAppAuthRestoreRequired);
        };
    }, [authenticateMiniApp, restoreMiniAppSession, shouldGateMiniApp]);

    // Standard web routes keep the normal auth flow.
    if (!shouldGateMiniApp) {
        return <>{children}</>;
    }

    // Authenticated users wait for the Mini App onboarding gate before cabinet routes render.
    if (isAuthenticated && !shouldHoldMiniAppContent) {
        return <>{children}</>;
    }

    const routeAuthError = isMiniAppRoutePath && telegramDetectionFinished && !effectiveIsMiniApp
        ? t('miniAppRequiredMessage')
        : authError;

    const retryMiniAppAuth = () => {
        restoreInFlight.current = true;
        hasAttempted.current = true;
        void authenticateMiniApp().finally(() => {
            restoreInFlight.current = false;
        });
    };

    const openTelegramBot = () => {
        const botUrl = getTelegramBotUrl();
        if (window.Telegram?.WebApp?.openTelegramLink) {
            window.Telegram.WebApp.openTelegramLink(botUrl);
            return;
        }
        window.location.href = botUrl;
    };

    const closeMiniApp = () => {
        window.Telegram?.WebApp?.close?.();
    };

    // Error state — keep Mini App routes gated to avoid exposing the web guest state.
    if (routeAuthError) {
        return (
            <motion.div
                initial={false}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center gap-4 p-8 text-center"
            >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 border border-red-500/20">
                    <AlertCircle className="h-6 w-6 text-red-400" aria-hidden="true" />
                </div>
                <p className="text-sm text-muted-foreground font-mono" role="alert">
                    {routeAuthError}
                </p>
                <div className="flex flex-wrap items-center justify-center gap-2">
                    <button
                        type="button"
                        onClick={retryMiniAppAuth}
                        className="inline-flex items-center gap-2 rounded-lg border border-grid-line/30 px-3 py-2 text-xs font-mono text-foreground transition-colors hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
                    >
                        <RotateCcw className="h-4 w-4" aria-hidden="true" />
                        {t('miniAppRetryTelegram')}
                    </button>
                    <button
                        type="button"
                        onClick={openTelegramBot}
                        className="inline-flex items-center gap-2 rounded-lg border border-grid-line/30 px-3 py-2 text-xs font-mono text-foreground transition-colors hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
                    >
                        <Send className="h-4 w-4" aria-hidden="true" />
                        {t('miniAppOpenBot')}
                    </button>
                    <button
                        type="button"
                        onClick={closeMiniApp}
                        className="inline-flex items-center gap-2 rounded-lg border border-grid-line/30 px-3 py-2 text-xs font-mono text-foreground transition-colors hover:border-red-400/40 hover:text-red-300 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-red-400"
                    >
                        <X className="h-4 w-4" aria-hidden="true" />
                        {t('miniAppClose')}
                    </button>
                </div>
                {!isMiniAppRoutePath ? children : null}
            </motion.div>
        );
    }

    // Loading state
    return (
        <motion.div
            initial={false}
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
