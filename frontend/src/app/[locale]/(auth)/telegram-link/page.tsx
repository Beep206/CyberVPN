'use client';

import { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useRouter } from '@/i18n/navigation';
import { motion } from 'motion/react';
import { Loader2, AlertCircle, RotateCcw, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/auth-store';

export default function TelegramLinkPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const t = useTranslations('Auth.telegram');
    const { loginWithBotLink } = useAuthStore();
    const [error, setError] = useState<string | null>(null);
    const hasProcessed = useRef(false);

    useEffect(() => {
        if (hasProcessed.current) return;
        hasProcessed.current = true;

        const token = searchParams.get('token');
        if (!token) {
            setError(t('botLinkInvalid'));
            return;
        }

        const handleAuth = async () => {
            try {
                await loginWithBotLink(token);
                router.push('/dashboard');
            } catch (err: unknown) {
                const axiosError = err as { response?: { data?: { detail?: string } } };
                const detail = axiosError?.response?.data?.detail;
                if (detail?.toLowerCase().includes('expired')) {
                    setError(t('botLinkExpired'));
                } else {
                    setError(detail || t('botLinkInvalid'));
                }
            }
        };

        handleAuth();
    }, [searchParams, loginWithBotLink, router, t]);

    const handleRetry = () => {
        setError(null);
        router.push('/login');
    };

    return (
        <div className="flex flex-col items-center justify-center gap-6 text-center">
            {error ? (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center gap-4 p-8 rounded-xl bg-terminal-surface/80 backdrop-blur-md border border-red-500/20"
                >
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 border border-red-500/20">
                        <AlertCircle className="h-6 w-6 text-red-400" aria-hidden="true" />
                    </div>
                    <p className="text-sm text-muted-foreground font-mono max-w-sm" role="alert">
                        {error}
                    </p>
                    <Button
                        onClick={handleRetry}
                        className="mt-2 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono cursor-pointer"
                        aria-label={t('botLinkAuth')}
                    >
                        <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" />
                        {t('botLinkAuth')}
                    </Button>
                </motion.div>
            ) : (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex flex-col items-center gap-4 p-8 rounded-xl bg-terminal-surface/80 backdrop-blur-md border border-grid-line/30"
                >
                    <div className="relative">
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-neon-cyan/10 border border-neon-cyan/20">
                            <Shield className="h-8 w-8 text-neon-cyan" aria-hidden="true" />
                        </div>
                        <Loader2 className="absolute -top-1 -right-1 h-6 w-6 text-neon-cyan animate-spin" aria-hidden="true" />
                    </div>
                    <div className="space-y-1">
                        <h2 className="font-display text-lg font-bold text-foreground">
                            {t('botLinkAuth')}
                        </h2>
                    </div>
                </motion.div>
            )}
        </div>
    );
}
