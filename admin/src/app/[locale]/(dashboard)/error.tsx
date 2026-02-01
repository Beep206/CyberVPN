'use client';

import { useEffect } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { useTranslations } from 'next-intl';

export default function DashboardError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    const t = useTranslations('Errors');

    useEffect(() => {
        console.error('[DashboardError]', error);
    }, [error]);

    return (
        <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-6 p-8">
            <div className="relative">
                <AlertTriangle className="h-20 w-20 text-neon-pink animate-pulse" />
                <div className="absolute inset-0 blur-xl bg-neon-pink/20 rounded-full" />
            </div>

            <h1 className="text-3xl font-display text-neon-pink tracking-widest">
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

            <div className="text-xs font-cyber text-neon-pink">
                {t('errorCode')}
            </div>

            <button
                onClick={reset}
                className="flex items-center gap-2 px-6 py-3 font-mono text-sm border border-neon-cyan text-neon-cyan hover:bg-neon-cyan/10 transition-colors mt-4"
                aria-label={t('retry')}
            >
                <RotateCcw className="h-4 w-4" />
                {t('retry')}
            </button>
        </div>
    );
}
