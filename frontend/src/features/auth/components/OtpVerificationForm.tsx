'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'motion/react';
import { Loader2, ArrowRight, ShieldCheck, RefreshCw, AlertCircle } from 'lucide-react';
import { AxiosError } from 'axios';
import { Button } from '@/components/ui/button';
import { AuthFormCard } from './AuthFormCard';
import { CyberOtpInput } from './CyberOtpInput';
import { cn } from '@/lib/utils';
import { useRouter } from '@/i18n/navigation';
import { authApi, OtpErrorResponse } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth-store';

export function OtpVerificationForm() {
    const t = useTranslations('Auth.verify');
    const router = useRouter();
    const searchParams = useSearchParams();

    // Get auth store for OTP verification and login
    const { verifyOtpAndLogin, isAuthenticated } = useAuthStore();

    // Get email from query params (passed from registration)
    const email = searchParams.get('email') || '';

    const [otp, setOtp] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isResending, setIsResending] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [errorCode, setErrorCode] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null);
    const [resendsRemaining, setResendsRemaining] = useState<number | null>(null);

    // Resend Timer Logic
    const [timeLeft, setTimeLeft] = useState(30);
    const canResend = timeLeft === 0 && !isResending;

    useEffect(() => {
        if (timeLeft > 0) {
            const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
            return () => clearTimeout(timer);
        }
    }, [timeLeft]);

    // Redirect to dashboard when authenticated
    useEffect(() => {
        if (isAuthenticated && success) {
            router.push('/dashboard');
        }
    }, [isAuthenticated, success, router]);

    const handleVerify = async () => {
        if (otp.length !== 6 || !email) return;

        setIsLoading(true);
        setError(null);
        setErrorCode(null);

        try {
            // Use auth store to verify OTP and auto-login (stores tokens + sets isAuthenticated)
            await verifyOtpAndLogin(email, otp);

            // Success - auth store now has user and isAuthenticated=true
            setSuccess(true);
            setIsLoading(false);

            // Redirect will happen via useEffect when isAuthenticated changes

        } catch (err) {
            const axiosError = err as AxiosError<{ detail: OtpErrorResponse }>;
            const errorData = axiosError.response?.data?.detail;

            if (typeof errorData === 'object' && errorData !== null) {
                setError(errorData.detail || 'Verification failed');
                setErrorCode(errorData.code || null);
                setAttemptsRemaining(errorData.attempts_remaining ?? null);
            } else if (typeof errorData === 'string') {
                setError(errorData);
            } else {
                setError('An error occurred. Please try again.');
            }

            setIsLoading(false);
            setOtp(''); // Clear OTP on error
        }
    };

    const handleResend = async () => {
        if (!canResend || !email) return;

        setIsResending(true);
        setError(null);
        setErrorCode(null);

        try {
            const response = await authApi.resendOtp({ email });

            // Success
            setResendsRemaining(response.data.resends_remaining);
            setTimeLeft(60); // Reset cooldown timer
            setOtp(''); // Clear current OTP

        } catch (err) {
            const axiosError = err as AxiosError<{ detail: OtpErrorResponse }>;
            const errorData = axiosError.response?.data?.detail;

            if (typeof errorData === 'object' && errorData !== null) {
                setError(errorData.detail || 'Failed to resend code');
                setErrorCode(errorData.code || null);
            } else if (typeof errorData === 'string') {
                setError(errorData);
            } else {
                setError('Failed to resend code. Please try again.');
            }
        } finally {
            setIsResending(false);
        }
    };

    // Show warning if no email
    if (!email) {
        return (
            <AuthFormCard
                title="SECURITY_CHECK"
                subtitle="VERIFICATION_REQUIRED"
                className="border-neon-cyan/30"
            >
                <div className="text-center space-y-4">
                    <AlertCircle className="w-12 h-12 text-yellow-500 mx-auto" />
                    <p className="text-muted-foreground font-mono">
                        No email provided. Please register first.
                    </p>
                    <Button
                        onClick={() => router.push('/register')}
                        className="bg-neon-cyan text-black hover:bg-neon-cyan/90"
                    >
                        Go to Registration
                    </Button>
                </div>
            </AuthFormCard>
        );
    }

    return (
        <AuthFormCard
            title="SECURITY_CHECK"
            subtitle="ENTER_ACCESS_CODE_SENT_TO_EMAIL"
            className="border-neon-cyan/30"
        >
            <div className="space-y-8">
                {/* Visual Status Indicator */}
                <div className="flex justify-center">
                    <motion.div
                        animate={{
                            scale: success ? 1.2 : 1,
                            color: success ? '#00ff88' : error ? '#ff0000' : '#00ffff'
                        }}
                        className={cn(
                            "p-4 rounded-full bg-terminal-bg border mb-2",
                            success ? "border-matrix-green shadow-[0_0_20px_var(--color-matrix-green)]" :
                                error ? "border-red-500 shadow-[0_0_20px_red]" :
                                    "border-neon-cyan/50 shadow-[0_0_15px_var(--color-neon-cyan)] animate-pulse"
                        )}
                    >
                        <ShieldCheck className="w-8 h-8" />
                    </motion.div>
                </div>

                {/* Email indicator */}
                <p className="text-center text-sm text-muted-foreground font-mono">
                    Code sent to: <span className="text-neon-cyan">{email}</span>
                </p>

                {/* OTP Input */}
                <div className="space-y-4">
                    <CyberOtpInput
                        value={otp}
                        onChange={(val) => {
                            setOtp(val);
                            if (error) {
                                setError(null);
                                setErrorCode(null);
                            }
                        }}
                        onComplete={handleVerify}
                        error={!!error}
                    />

                    <AnimatePresence>
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -5 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="text-center space-y-1"
                            >
                                <p className="text-red-500 font-mono text-sm">
                                    {error}
                                </p>
                                {attemptsRemaining !== null && attemptsRemaining > 0 && (
                                    <p className="text-yellow-500 font-mono text-xs">
                                        {attemptsRemaining} attempts remaining
                                    </p>
                                )}
                                {errorCode === 'OTP_EXHAUSTED' && (
                                    <p className="text-yellow-500 font-mono text-xs">
                                        Please request a new code
                                    </p>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Actions */}
                <div className="space-y-4">
                    <div className="flex justify-center">
                        <Button
                            onClick={handleVerify}
                            disabled={otp.length !== 6 || isLoading || success}
                            className={cn(
                                "min-w-[200px] h-12 font-mono font-bold tracking-wider text-lg transition-all",
                                "bg-neon-cyan text-black hover:bg-neon-cyan/90 border-0",
                                "shadow-[0_0_20px_rgba(0,255,255,0.4)] hover:shadow-[0_0_30px_rgba(0,255,255,0.6)]",
                                "disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed"
                            )}
                        >
                            {isLoading ? (
                                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                            ) : success ? (
                                "ACCESS_GRANTED"
                            ) : (
                                <span className="flex items-center">
                                    VERIFY_IDENTITY <ArrowRight className="ml-2 w-5 h-5" />
                                </span>
                            )}
                        </Button>
                    </div>

                    <div className="text-center">
                        <button
                            onClick={handleResend}
                            disabled={!canResend || isResending}
                            className={cn(
                                "text-sm font-mono transition-colors flex items-center justify-center mx-auto gap-2",
                                canResend && !isResending
                                    ? "text-neon-cyan hover:text-white underline underline-offset-4 cursor-pointer"
                                    : "text-muted-foreground cursor-default"
                            )}
                        >
                            {isResending ? (
                                <>
                                    <Loader2 className="w-3 h-3 animate-spin" /> Sending...
                                </>
                            ) : canResend ? (
                                <>
                                    <RefreshCw className="w-3 h-3" /> RESEND_CODE
                                    {resendsRemaining !== null && ` (${resendsRemaining} left)`}
                                </>
                            ) : (
                                <span>RESEND_IN_{timeLeft.toString().padStart(2, '0')}s</span>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </AuthFormCard>
    );
}
