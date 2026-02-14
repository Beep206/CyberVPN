'use client';

import { useEffect, useState, startTransition } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useRouter } from '@/i18n/navigation';
import { motion } from 'motion/react';
import { Loader2, AlertCircle, RotateCcw, Shield, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/auth-store';

// Module-level guard: survives React Strict Mode unmount/remount cycles
// (useRef is re-initialized on remount, so it can't prevent double-fire)
const PROCESSED_TOKENS = new Set<string>();

export default function MagicLinkVerifyPage() {
    const t = useTranslations('Auth.magicLink.verify');
    const searchParams = useSearchParams();
    const router = useRouter();
    const { verifyMagicLink, isAuthenticated } = useAuthStore();
    const [error, setError] = useState<string | null>(null);
    const [verifying, setVerifying] = useState(true);
    const [verified, setVerified] = useState(false);

    useEffect(() => {
        const token = searchParams.get('token');

        if (!token) {
            startTransition(() => {
                setError(t('missingToken'));
                setVerifying(false);
            });
            return;
        }

        if (PROCESSED_TOKENS.has(token)) return;
        PROCESSED_TOKENS.add(token);

        const verify = async () => {
            try {
                await verifyMagicLink(token);
                setVerifying(false);
                setVerified(true);
            } catch (err: unknown) {
                if (useAuthStore.getState().isAuthenticated) {
                    setVerifying(false);
                    setVerified(true);
                    return;
                }

                const axiosError = err as { response?: { data?: { detail?: string } } };
                setError(
                    axiosError.response?.data?.detail ||
                    t('invalidOrExpired')
                );
                setVerifying(false);
            }
        };

        verify();
    }, [searchParams, verifyMagicLink, t]);

    useEffect(() => {
        if (verified && isAuthenticated) {
            router.push('/dashboard');
        }
    }, [verified, isAuthenticated, router]);

    return (
        <div className="flex flex-col items-center justify-center gap-6 text-center">
            {error ? (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center gap-4 p-8 rounded-xl bg-terminal-surface/80 backdrop-blur-md border border-red-500/20"
                >
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 border border-red-500/20">
                        <AlertCircle className="h-6 w-6 text-red-400" aria-label={t('errorIcon')} />
                    </div>
                    <div className="space-y-2">
                        <h2 className="font-display text-lg font-bold text-foreground">
                            {t('failed')}
                        </h2>
                        <p className="text-sm text-muted-foreground font-mono max-w-sm" role="alert">
                            {error}
                        </p>
                    </div>
                    <Button
                        onClick={() => router.push('/magic-link')}
                        className="mt-2 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono cursor-pointer"
                        aria-label={t('requestNewLink')}
                    >
                        <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" />
                        {t('requestNewLink')}
                    </Button>
                </motion.div>
            ) : verifying ? (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex flex-col items-center gap-4 p-8 rounded-xl bg-terminal-surface/80 backdrop-blur-md border border-grid-line/30"
                >
                    <div className="relative">
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-neon-cyan/10 border border-neon-cyan/20">
                            <Shield className="h-8 w-8 text-neon-cyan" aria-label={t('verifyIcon')} />
                        </div>
                        <Loader2 className="absolute -top-1 -right-1 h-6 w-6 text-neon-cyan animate-spin" aria-hidden="true" />
                    </div>
                    <div className="space-y-1">
                        <h2 className="font-display text-lg font-bold text-foreground">
                            {t('verifying')}
                        </h2>
                        <p className="text-xs text-muted-foreground font-mono">
                            {t('validating')}
                        </p>
                    </div>
                </motion.div>
            ) : (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center gap-4 p-8 rounded-xl bg-terminal-surface/80 backdrop-blur-md border border-matrix-green/20"
                >
                    <CheckCircle className="h-12 w-12 text-matrix-green" aria-label={t('successIcon')} />
                    <h2 className="font-display text-lg font-bold text-foreground">
                        {t('verified')}
                    </h2>
                    <p className="text-xs text-muted-foreground font-mono">
                        {t('redirecting')}
                    </p>
                </motion.div>
            )}
        </div>
    );
}
