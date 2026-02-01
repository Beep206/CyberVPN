import { AlertCircle } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import Link from 'next/link';

export default async function NotFound() {
    const t = await getTranslations('Errors');

    return (
        <div className="flex flex-col items-center justify-center min-h-screen text-center space-y-6 p-8 bg-terminal-bg">
            <div className="relative">
                <div className="text-[8rem] font-display text-neon-cyan leading-none tracking-widest neon-text">
                    404
                </div>
                <div className="absolute inset-0 blur-2xl bg-neon-cyan/10 rounded-full" />
            </div>

            <div className="relative">
                <AlertCircle className="h-12 w-12 text-neon-pink mx-auto mb-4" />
            </div>

            <h1 className="text-3xl font-display text-neon-pink tracking-widest">
                {t('notFoundTitle')}
            </h1>

            <p className="text-muted-foreground font-mono max-w-md">
                {t('notFoundDescription')}
            </p>

            <div className="text-xs font-cyber text-neon-pink mt-2">
                {t('notFoundCode')}
            </div>

            <Link
                href="/dashboard"
                className="flex items-center gap-2 px-6 py-3 font-mono text-sm border border-matrix-green text-matrix-green hover:bg-matrix-green/10 transition-colors mt-8"
            >
                {t('notFoundReturn')}
            </Link>
        </div>
    );
}
