'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from '@/i18n/navigation';
import { motion } from 'motion/react';
import Link from 'next/link';
import { UserPlus, Loader2, Check, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    AuthFormCard,
    CyberInput,
    SocialAuthButtons,
    AuthDivider,
    PasswordStrengthMeter,
    RateLimitCountdown,
    useIsRateLimited,
} from '@/features/auth/components';
import { useAuthStore } from '@/stores/auth-store';

export default function RegisterPage() {
    const t = useTranslations('Auth.register');
    const router = useRouter();

    const { register, isLoading, error, isAuthenticated, clearError } = useAuthStore();
    const isRateLimited = useIsRateLimited();

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [acceptTerms, setAcceptTerms] = useState(false);

    const passwordsMatch = password === confirmPassword && confirmPassword.length > 0;
    const canSubmit = email && password && confirmPassword && acceptTerms && passwordsMatch && !isRateLimited;
    const errorRef = useRef<HTMLDivElement>(null);

    // Redirect if already authenticated (auto-login after registration)
    useEffect(() => {
        if (isAuthenticated) {
            router.push('/dashboard');
        }
    }, [isAuthenticated, router]);

    // Clear error on mount
    useEffect(() => {
        clearError();
    }, [clearError]);

    // Focus management for errors
    useEffect(() => {
        if (error && !isRateLimited && errorRef.current) {
            errorRef.current.focus();
        }
    }, [error, isRateLimited]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!canSubmit) return;

        try {
            await register(email, password);
            // Redirect to OTP verification page with email
            router.push(`/verify?email=${encodeURIComponent(email)}`);
        } catch {
            // Error is already set in the store
        }
    };

    return (
        <AuthFormCard
            title={t('title')}
            subtitle={t('subtitle')}
        >
            {/* Social auth */}
            <SocialAuthButtons disabled={isLoading || isRateLimited} />

            <AuthDivider text={t('divider')} />

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

            {/* Register form */}
            <form onSubmit={handleSubmit} className="space-y-5">
                <CyberInput
                    label={t('emailLabel')}
                    type="email"
                    prefix="email"
                    placeholder="user@cybervpn.io"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    disabled={isLoading || isRateLimited}
                />

                <div className="space-y-2">
                    <CyberInput
                        label={t('passwordLabel')}
                        type="password"
                        prefix="pass"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        autoComplete="new-password"
                        disabled={isLoading || isRateLimited}
                    />
                    <PasswordStrengthMeter password={password} />
                </div>

                <CyberInput
                    label={t('confirmPasswordLabel')}
                    type="password"
                    prefix="confirm"
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    disabled={isLoading || isRateLimited}
                    error={confirmPassword && !passwordsMatch ? t('passwordMismatch') : undefined}
                    success={passwordsMatch}
                />

                {/* Terms checkbox */}
                <label className="flex items-start gap-3 cursor-pointer group">
                    <div className="relative mt-0.5">
                        <input
                            type="checkbox"
                            checked={acceptTerms}
                            onChange={(e) => setAcceptTerms(e.target.checked)}
                            className="peer sr-only"
                            required
                            aria-label={t('acceptTerms')}
                        />
                        <div className="w-5 h-5 rounded border border-grid-line bg-terminal-bg peer-checked:bg-neon-cyan peer-checked:border-neon-cyan peer-focus:ring-2 peer-focus:ring-neon-cyan/50 transition-all flex items-center justify-center">
                            {acceptTerms && <Check className="h-3 w-3 text-black" />}
                        </div>
                    </div>
                    <span className="text-xs text-muted-foreground font-mono leading-relaxed group-hover:text-foreground transition-colors">
                        {t('acceptTerms')}{' '}
                        <Link href="/terms" className="text-neon-cyan hover:underline">
                            {t('termsLink')}
                        </Link>{' '}
                        {t('and')}{' '}
                        <Link href="/privacy-policy" className="text-neon-cyan hover:underline">
                            {t('privacyLink')}
                        </Link>
                    </span>
                </label>

                {/* Submit button */}
                <motion.div
                    whileHover={{ scale: canSubmit ? 1.01 : 1 }}
                    whileTap={{ scale: canSubmit ? 0.99 : 1 }}
                    className="flex justify-center"
                >
                    <Button
                        type="submit"
                        disabled={isLoading || !canSubmit}
                        className="min-w-[200px] h-12 bg-neon-purple hover:bg-neon-purple/90 text-white font-bold font-mono tracking-wider shadow-lg shadow-neon-purple/20 hover:shadow-neon-purple/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                        aria-label={isLoading ? t('submitting') : t('submitButton')}
                    >
                        {isLoading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                {t('submitting')}
                            </>
                        ) : (
                            <>
                                <UserPlus className="mr-2 h-4 w-4" />
                                {t('submitButton')}
                            </>
                        )}
                    </Button>
                </motion.div>
            </form>

            {/* Login link */}
            <p className="mt-6 text-center text-sm text-muted-foreground font-mono">
                {t('hasAccount')}{' '}
                <Link
                    href="/login"
                    className="text-neon-cyan hover:text-neon-cyan/80 transition-colors underline underline-offset-4"
                >
                    {t('signInLink')}
                </Link>
            </p>
        </AuthFormCard>
    );
}
