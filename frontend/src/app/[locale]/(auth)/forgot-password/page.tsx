'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import Link from 'next/link';
import { KeyRound, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    AuthFormCard,
    CyberInput,
    RateLimitCountdown,
    useIsRateLimited,
} from '@/features/auth/components';
import { useAuthStore } from '@/stores/auth-store';
import { authApi } from '@/lib/api/auth';
import { RateLimitError } from '@/lib/api/client';

export default function ForgotPasswordPage() {
    const t = useTranslations('Auth.forgotPassword');
    const { isLoading: storeLoading, clearError } = useAuthStore();
    const isRateLimited = useIsRateLimited();

    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const errorRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        clearError();
    }, [clearError]);

    // Focus management for errors
    useEffect(() => {
        if (error && !isRateLimited && errorRef.current) {
            errorRef.current.focus();
        }
    }, [error, isRateLimited]);

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);
        try {
            await authApi.forgotPassword({ email });
            setSent(true);
        } catch (err: unknown) {
            if (err instanceof RateLimitError) {
                setError(err.message);
            } else {
                // Always show success to prevent email enumeration
                setSent(true);
            }
        } finally {
            setIsLoading(false);
        }
    };

    const loading = isLoading || storeLoading;

    return (
        <AuthFormCard
            title={t('title')}
            subtitle={t('subtitle')}
        >
            {/* Rate limit countdown */}
            <RateLimitCountdown />

            {/* Error message */}
            {error && !isRateLimited && (
                <motion.div
                    ref={errorRef}
                    role="alert"
                    tabIndex={-1}
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-red-500/50"
                >
                    <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span>{error}</span>
                </motion.div>
            )}

            {sent ? (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center gap-4 py-6"
                >
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-matrix-green/10 border border-matrix-green/20">
                        <CheckCircle className="h-8 w-8 text-matrix-green" aria-hidden="true" />
                    </div>
                    <div className="text-center space-y-2">
                        <h3 className="font-display text-lg font-bold text-foreground">
                            {t('successTitle')}
                        </h3>
                        <p className="text-sm text-muted-foreground font-mono">
                            {t('successMessage')}{' '}
                            <span className="text-neon-cyan">{email}</span>
                        </p>
                        <p className="text-xs text-muted-foreground/60 font-mono">
                            {t('successExpiry')}
                        </p>
                    </div>

                    {/* Navigate to reset password page */}
                    <Link href={`/reset-password?email=${encodeURIComponent(email)}`}>
                        <Button
                            className="mt-2 min-w-[200px] h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all cursor-pointer"
                            aria-label={t('continueToReset')}
                        >
                            <KeyRound className="mr-2 h-4 w-4" aria-hidden="true" />
                            {t('continueToReset')}
                        </Button>
                    </Link>

                    <Button
                        onClick={() => {
                            setSent(false);
                            setError(null);
                        }}
                        variant="outline"
                        className="font-mono text-sm cursor-pointer border-grid-line/30 hover:border-neon-cyan/50"
                        aria-label={t('sendAgain')}
                    >
                        {t('sendAgain')}
                    </Button>
                </motion.div>
            ) : (
                <form onSubmit={handleSubmit} className="space-y-5">
                    <CyberInput
                        label={t('emailLabel')}
                        type="email"
                        prefix="email"
                        placeholder={t('emailPlaceholder')}
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        autoComplete="email"
                        disabled={loading || isRateLimited}
                    />

                    {/* Submit button */}
                    <motion.div
                        whileHover={{ scale: loading || isRateLimited ? 1 : 1.01 }}
                        whileTap={{ scale: loading || isRateLimited ? 1 : 0.99 }}
                        className="flex justify-center"
                    >
                        <Button
                            type="submit"
                            disabled={loading || isRateLimited || !email}
                            className="min-w-[200px] h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                            aria-label={loading ? t('submitting') : t('submitButton')}
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                                    {t('submitting')}
                                </>
                            ) : (
                                <>
                                    <KeyRound className="mr-2 h-4 w-4" aria-hidden="true" />
                                    {t('submitButton')}
                                </>
                            )}
                        </Button>
                    </motion.div>
                </form>
            )}

            {/* Back to login link */}
            <p className="mt-6 text-center text-sm text-muted-foreground font-mono">
                <Link
                    href="/login"
                    className="text-neon-cyan hover:text-neon-cyan/80 transition-colors underline underline-offset-4"
                >
                    {t('backToLogin')}
                </Link>
            </p>
        </AuthFormCard>
    );
}
