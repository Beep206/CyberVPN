'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import { Loader2, ArrowRight, ShieldCheck, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AuthFormCard } from './AuthFormCard';
import { CyberOtpInput } from './CyberOtpInput';
import { cn } from '@/lib/utils';
import { useRouter } from '@/i18n/navigation';

export function OtpVerificationForm() {
    const t = useTranslations('Auth.verify'); // Assuming translations exist or will fallback
    const router = useRouter();

    const [otp, setOtp] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(false);
    const [success, setSuccess] = useState(false);

    // Resend Timer Logic
    const [timeLeft, setTimeLeft] = useState(30);
    const canResend = timeLeft === 0;

    useEffect(() => {
        if (timeLeft > 0) {
            const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
            return () => clearTimeout(timer);
        }
    }, [timeLeft]);

    const handleVerify = async () => {
        if (otp.length !== 6) return;

        setIsLoading(true);
        setError(false);

        // Simulate API call
        setTimeout(() => {
            if (otp === '123456') {
                setSuccess(true);
                setTimeout(() => {
                    router.push('/dashboard');
                }, 1000);
            } else {
                setError(true);
                setIsLoading(false);
                // Shake effect or error feedback handled by CyberOtpInput prop
            }
        }, 1500);
    };

    const handleResend = () => {
        if (!canResend) return;
        setTimeLeft(60);
        // Trigger resend API
    };

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
                        {success ? (
                            <ShieldCheck className="w-8 h-8" />
                        ) : (
                            <ShieldCheck className="w-8 h-8" />
                        )}
                    </motion.div>
                </div>

                {/* OTP Input */}
                <div className="space-y-4">
                    <CyberOtpInput
                        value={otp}
                        onChange={(val) => {
                            setOtp(val);
                            if (error) setError(false);
                        }}
                        onComplete={handleVerify}
                        error={error}
                    />

                    <AnimatePresence>
                        {error && (
                            <motion.p
                                initial={{ opacity: 0, y: -5 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="text-center text-red-500 font-mono text-sm"
                            >
                                INVALID_ACCESS_CODE.TRY_AGAIN.
                            </motion.p>
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
                            disabled={!canResend}
                            className={cn(
                                "text-sm font-mono transition-colors flex items-center justify-center mx-auto gap-2",
                                canResend
                                    ? "text-neon-cyan hover:text-white underline underline-offset-4 cursor-pointer"
                                    : "text-muted-foreground cursor-default"
                            )}
                        >
                            {canResend ? (
                                <>
                                    <RefreshCw className="w-3 h-3" /> RESEND_CODE
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
