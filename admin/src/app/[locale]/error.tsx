'use client';

import { useEffect } from 'react';
import { AlertTriangle, RotateCcw, Home } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useRouter } from '@/i18n/navigation';

export default function LocaleError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    const t = useTranslations('Errors');
    const router = useRouter();

    useEffect(() => {
        console.error('[LocaleError]', error);
    }, [error]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen text-center space-y-6 p-8 bg-terminal-bg">
            <div className="relative">
                <AlertTriangle className="h-24 w-24 text-neon-pink animate-pulse" />
                <div className="absolute inset-0 blur-xl bg-neon-pink/20 rounded-full" />
            </div>

            <h1 className="text-4xl font-display text-neon-pink tracking-widest neon-text">
                {t('title')}
            </h1>

            <p className="text-muted-foreground font-mono max-w-md">
                {t('description')}
            </p>

            {error.digest && (
                <code className="text-xs font-cyber text-neon-cyan/60">
                    DIGEST: {error.digest}
                </code>
            )}

            <div className="text-xs font-cyber text-neon-pink mt-2">
                {t('errorCode')}
            </div>

            <div className="flex gap-4 mt-8">
                <button
                    onClick={reset}
                    className="flex items-center gap-2 px-6 py-3 font-mono text-sm border border-neon-cyan text-neon-cyan hover:bg-neon-cyan/10 transition-colors"
                    aria-label={t('retry')}
                >
                    <RotateCcw className="h-4 w-4" />
                    {t('retry')}
                </button>
                <button
                    onClick={() => router.push('/dashboard')}
                    className="flex items-center gap-2 px-6 py-3 font-mono text-sm border border-matrix-green text-matrix-green hover:bg-matrix-green/10 transition-colors"
                    aria-label={t('goHome')}
                >
                    <Home className="h-4 w-4" />
                    {t('goHome')}
                </button>
            </div>
        </div>
    );
}
