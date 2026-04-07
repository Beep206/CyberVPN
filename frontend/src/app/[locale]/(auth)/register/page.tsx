'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter } from 'next/navigation'; // Switching to native router to prevent double-locale issues
import { motion } from 'motion/react';
import Link from 'next/link';
import { UserPlus, Loader2, Check, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
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
    const locale = useLocale();

    const { register, oauthLogin, isLoading, error, isAuthenticated, clearError } = useAuthStore();
    const isRateLimited = useIsRateLimited();

    const [usernameOnly, setUsernameOnly] = useState(false);
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [acceptTerms, setAcceptTerms] = useState(false);
    const [marketingConsent, setMarketingConsent] = useState(false);
    const isEmailMode = !usernameOnly;
    const identifierValue = isEmailMode ? email : username;
    const identifierLabel = isEmailMode ? t('emailLabel') : t('usernameLabel');
    const identifierPrefix = isEmailMode ? 'email' : 'user';
    const identifierPlaceholder = isEmailMode ? 'user@cybervpn.io' : t('usernamePlaceholder');
    const identifierType = isEmailMode ? 'email' : 'text';
    const identifierAutocomplete = isEmailMode ? 'email' : 'username';

    const passwordsMatch = password === confirmPassword && confirmPassword.length > 0;
    const canSubmit = usernameOnly
        ? username && password && confirmPassword && acceptTerms && passwordsMatch && !isRateLimited
        : email && password && confirmPassword && acceptTerms && passwordsMatch && !isRateLimited;
    const errorRef = useRef<HTMLDivElement>(null);

    // Redirect if already authenticated (auto-login after registration)
    useEffect(() => {
        if (isAuthenticated) {
            router.push(`/${locale}/dashboard`);
        }
    }, [isAuthenticated, router, locale]);

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

    const handleOAuthLogin = (provider: string) => {
        oauthLogin(provider as Parameters<typeof oauthLogin>[0]).catch(() => {
            // Ignore intentional cancellations or let the store handle the error state
        });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!canSubmit) return;

        try {
            if (usernameOnly) {
                await register(username, password, { mode: 'username', tos_accepted: acceptTerms, marketing_consent: marketingConsent });
                router.push(`/${locale}/login?registered=true`);
            } else {
                await register(email, password, { mode: 'email', tos_accepted: acceptTerms, marketing_consent: marketingConsent });
                router.push(`/${locale}/verify?email=${encodeURIComponent(email)}`);
            }
        } catch {
            // Error is already set in the store
        }
    };

    return (
        <AuthFormCard
            title={t('title')}
            subtitle={t('subtitle')}
            className="keyboard-safe-bottom"
        >
            {/* Social auth */}
            <SocialAuthButtons
                onProviderClick={handleOAuthLogin}
                disabled={isLoading || isRateLimited}
            />

            <AuthDivider text={t('divider')} />

            {/* Registration mode toggle */}
            <div className="flex gap-2 font-mono text-xs">
                <button
                    type="button"
                    onClick={() => setUsernameOnly(false)}
                    aria-pressed={!usernameOnly}
                    className={cn(
                        "touch-target flex-1 px-3 py-2 rounded-lg border transition-all cursor-pointer",
                        !usernameOnly
                            ? "border-neon-cyan/50 bg-neon-cyan/10 text-neon-cyan"
                            : "border-grid-line/30 text-muted-foreground hover:border-grid-line/50"
                    )}
                    aria-label={t('registerModeEmail')}
                >
                    {t('registerModeEmail')}
                </button>
                <button
                    type="button"
                    onClick={() => setUsernameOnly(true)}
                    aria-pressed={usernameOnly}
                    className={cn(
                        "touch-target flex-1 px-3 py-2 rounded-lg border transition-all cursor-pointer",
                        usernameOnly
                            ? "border-neon-purple/50 bg-neon-purple/10 text-neon-purple"
                            : "border-grid-line/30 text-muted-foreground hover:border-grid-line/50"
                    )}
                    aria-label={t('registerModeUsername')}
                >
                    {t('registerModeUsername')}
                </button>
            </div>

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

            {/* Register form */}
            <form onSubmit={handleSubmit} className="keyboard-safe-bottom space-y-5" aria-busy={isLoading}>
                <CyberInput
                    label={identifierLabel}
                    type={identifierType}
                    prefix={identifierPrefix}
                    placeholder={identifierPlaceholder}
                    value={identifierValue}
                    onChange={(e) => {
                        if (isEmailMode) {
                            setEmail(e.target.value);
                            return;
                        }

                        setUsername(e.target.value);
                    }}
                    required
                    autoComplete={identifierAutocomplete}
                    disabled={isLoading || isRateLimited}
                    className="mobile-form-input"
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
                        className="mobile-form-input"
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
                    className="mobile-form-input"
                />

                {/* Terms checkbox */}
                <label className="touch-target flex items-start gap-3 cursor-pointer group">
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
                        <Link href="/terms" className="touch-target inline-flex items-center text-neon-cyan hover:underline">
                            {t('termsLink')}
                        </Link>{' '}
                        {t('and')}{' '}
                        <Link href="/privacy-policy" className="touch-target inline-flex items-center text-neon-cyan hover:underline">
                            {t('privacyLink')}
                        </Link>
                    </span>
                </label>

                {/* Marketing consent checkbox */}
                <label className="touch-target flex items-start gap-3 cursor-pointer group mt-4">
                    <div className="relative mt-0.5">
                        <input
                            type="checkbox"
                            checked={marketingConsent}
                            onChange={(e) => setMarketingConsent(e.target.checked)}
                            className="peer sr-only"
                            aria-label={t.has('marketingConsentLabel') ? t('marketingConsentLabel') : 'I want to receive marketing emails'}
                        />
                        <div className="w-5 h-5 rounded border border-grid-line bg-terminal-bg peer-checked:bg-neon-cyan peer-checked:border-neon-cyan peer-focus:ring-2 peer-focus:ring-neon-cyan/50 transition-all flex items-center justify-center">
                            {marketingConsent && <Check className="h-3 w-3 text-black" />}
                        </div>
                    </div>
                    <span className="text-xs text-muted-foreground font-mono leading-relaxed group-hover:text-foreground transition-colors">
                        {t.has('marketingConsentLabel') ? t('marketingConsentLabel') : 'I want to receive news, special offers, and other updates'}
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
                        touchTarget="comfortable"
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
