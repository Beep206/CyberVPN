'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import Link from 'next/link';
import { Mail, Loader2, CheckCircle, AlertCircle, RefreshCw, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    AuthFormCard,
    CyberInput,
    CyberOtpInput,
    RateLimitCountdown,
    useIsRateLimited,
} from '@/features/auth/components';
import { useAuthStore } from '@/stores/auth-store';
import { useRouter } from '@/i18n/navigation';

const RESEND_COOLDOWN_SECONDS = 60;
const OTP_LENGTH = 6;

export default function MagicLinkPage() {
    const t = useTranslations('Auth.magicLink');
    const router = useRouter();
    const { requestMagicLink, verifyMagicLinkOtp, isLoading, error, clearError, isAuthenticated } = useAuthStore();
    const isRateLimited = useIsRateLimited();

    const [email, setEmail] = useState('');
    const [sent, setSent] = useState(false);
    const [resendTimeLeft, setResendTimeLeft] = useState(0);
    const [isResending, setIsResending] = useState(false);
    const [otpCode, setOtpCode] = useState('');
    const [isVerifyingCode, setIsVerifyingCode] = useState(false);
    const [otpError, setOtpError] = useState<string | null>(null);
    const canResend = resendTimeLeft === 0 && !isResending;
    const errorRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        clearError();
    }, [clearError]);

    // Resend cooldown timer
    useEffect(() => {
        if (resendTimeLeft > 0) {
            const timer = setTimeout(() => setResendTimeLeft(resendTimeLeft - 1), 1000);
            return () => clearTimeout(timer);
        }
    }, [resendTimeLeft]);

    // Focus management for errors
    useEffect(() => {
        if (error && !isRateLimited && errorRef.current) {
            errorRef.current.focus();
        }
    }, [error, isRateLimited]);

    // Redirect to dashboard when authenticated
    useEffect(() => {
        if (isAuthenticated) {
            router.push('/dashboard');
        }
    }, [isAuthenticated, router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await requestMagicLink(email);
            setSent(true);
            setResendTimeLeft(RESEND_COOLDOWN_SECONDS);
        } catch {
            // Error handled by store
        }
    };

    const handleResend = async () => {
        if (!canResend) return;
        setIsResending(true);
        try {
            await requestMagicLink(email);
            setResendTimeLeft(RESEND_COOLDOWN_SECONDS);
        } catch {
            // Error handled by store
        } finally {
            setIsResending(false);
        }
    };

    const handleVerifyCode = async (code?: string) => {
        const codeToVerify = code ?? otpCode;
        if (codeToVerify.length !== OTP_LENGTH || !email) return;

        setIsVerifyingCode(true);
        setOtpError(null);
        try {
            await verifyMagicLinkOtp(email, codeToVerify);
            // Redirect handled by useEffect on isAuthenticated change
        } catch (err: unknown) {
            const axiosError = err as { response?: { data?: { detail?: string } } };
            const message = axiosError?.response?.data?.detail || 'Code verification failed';
            setOtpError(message);
            setOtpCode('');
        } finally {
            setIsVerifyingCode(false);
        }
    };

    return (
        <AuthFormCard
            title={t('title')}
            subtitle={t('subtitle')}
        >
            {/* Rate limit countdown */}
            <RateLimitCountdown />

            {/* Error message */}
            <div aria-live="polite" aria-atomic="true">
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
            </div>

            {sent ? (
                <motion.div
                    aria-live="assertive"
                    aria-atomic="true"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center gap-4 py-6"
                >
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-matrix-green/10 border border-matrix-green/20">
                        <CheckCircle className="h-8 w-8 text-matrix-green" aria-label={t('verify.successIcon')} />
                    </div>
                    <div className="text-center space-y-2">
                        <h3 className="font-display text-lg font-bold text-foreground">
                            {t('checkInbox')}
                        </h3>
                        <p className="text-sm text-muted-foreground font-mono">
                            {t('sentTo')}{' '}
                            <span className="text-neon-cyan">{email}</span>
                        </p>
                        <p className="text-xs text-muted-foreground-low font-mono">
                            {t('expiresIn')}
                        </p>
                    </div>

                    {/* OTP Code Entry Section */}
                    <div className="w-full mt-4 space-y-4">
                        <div className="flex items-center gap-3">
                            <div className="flex-1 h-px bg-grid-line/30" />
                            <p className="text-xs text-muted-foreground font-mono flex items-center gap-1.5">
                                <ShieldCheck className="h-3.5 w-3.5 text-neon-cyan" aria-hidden="true" />
                                {t('orEnterCode')}
                            </p>
                            <div className="flex-1 h-px bg-grid-line/30" />
                        </div>

                        <div className="space-y-4">
                            <CyberOtpInput
                                value={otpCode}
                                onChange={(val) => {
                                    setOtpCode(val);
                                    if (otpError) setOtpError(null);
                                }}
                                onComplete={handleVerifyCode}
                                error={!!otpError}
                            />

                            <AnimatePresence>
                                {otpError && (
                                    <motion.p
                                        initial={{ opacity: 0, y: -5 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0 }}
                                        className="text-center text-red-500 font-mono text-sm"
                                    >
                                        {otpError}
                                    </motion.p>
                                )}
                            </AnimatePresence>

                            {isVerifyingCode && (
                                <div className="flex items-center justify-center gap-2 text-neon-cyan font-mono text-sm">
                                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                                    {t('verifyingCode')}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Resend button */}
                    <button
                        onClick={handleResend}
                        disabled={!canResend || isResending}
                        className={`mt-2 text-sm font-mono transition-colors flex items-center justify-center mx-auto gap-2 ${
                            canResend && !isResending
                                ? 'text-neon-cyan hover:text-white underline underline-offset-4 cursor-pointer'
                                : 'text-muted-foreground cursor-default'
                        }`}
                        aria-label={t('sendAgain')}
                    >
                        {isResending ? (
                            <>
                                <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" />
                                {t('submitting')}
                            </>
                        ) : canResend ? (
                            <>
                                <RefreshCw className="w-3 h-3" aria-hidden="true" />
                                {t('sendAgain')}
                            </>
                        ) : (
                            <span>{t('sendAgain')} ({resendTimeLeft}s)</span>
                        )}
                    </button>
                </motion.div>
            ) : (
                <form onSubmit={handleSubmit} className="space-y-5" aria-busy={isLoading}>
                    <CyberInput
                        label={t('emailLabel')}
                        type="email"
                        prefix="email"
                        placeholder={t('emailPlaceholder')}
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        autoComplete="email"
                        disabled={isLoading || isRateLimited}
                    />

                    {/* Submit button */}
                    <motion.div
                        whileHover={{ scale: isLoading || isRateLimited ? 1 : 1.01 }}
                        whileTap={{ scale: isLoading || isRateLimited ? 1 : 0.99 }}
                        className="flex justify-center"
                    >
                        <Button
                            type="submit"
                            disabled={isLoading || isRateLimited || !email}
                            className="min-w-[200px] h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                            aria-label={isLoading ? t('submitting') : t('submitButton')}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                                    {t('submitting')}
                                </>
                            ) : (
                                <>
                                    <Mail className="mr-2 h-4 w-4" aria-hidden="true" />
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
