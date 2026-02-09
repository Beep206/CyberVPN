'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { useAuthStore } from '@/stores/auth-store';
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
    const t = useTranslations('Auth.telegram');
    const { telegramMiniAppAuth, isAuthenticated, isMiniApp } = useAuthStore();
    const [authError, setAuthError] = useState<string | null>(null);
    const hasAttempted = useRef(false);

    useEffect(() => {
        if (!isMiniApp || isAuthenticated || hasAttempted.current) return;
        hasAttempted.current = true;

        const doAuth = async () => {
            try {
                await telegramMiniAppAuth();
                router.push('/dashboard');
            } catch {
                setAuthError(t('miniAppAutoAuth'));
            }
        };

        doAuth();
    }, [isMiniApp, isAuthenticated, telegramMiniAppAuth, router, t]);

    // Not a Mini App — render children (standard login flow)
    if (!isMiniApp) {
        return <>{children}</>;
    }

    // Authenticated — render children
    if (isAuthenticated) {
        return <>{children}</>;
    }

    // Error state — show error with fallback
    if (authError) {
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
                    {authError}
                </p>
                {children}
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
