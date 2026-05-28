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
import {
    normalizeEmailInput,
    validateEmailInput,
    validatePasswordInput,
    type EmailValidationCode,
    type PasswordValidationCode,
} from '@/features/auth/lib/validation';
import { useAuthStore } from '@/stores/auth-store';

const FALLBACK_VALIDATION_MESSAGES: Record<EmailValidationCode | PasswordValidationCode | 'passwordMismatch', string> = {
    emailRequired: 'Email is required',
    emailInvalid: 'Enter a valid email address',
    emailNoSpaces: 'Email must not contain spaces',
    emailTooLong: 'Email is too long',
    passwordRequired: 'Password is required',
    passwordMinLength: 'Password must be at least 12 characters',
    passwordUppercase: 'Password must contain one uppercase letter',
    passwordLowercase: 'Password must contain one lowercase letter',
    passwordNumber: 'Password must contain one number',
    passwordSpecial: 'Password must contain one special character',
    passwordLatinLayout: 'Use Latin letters, digits and supported symbols only',
    passwordCommon: 'Choose a less common password',
    passwordRepeated: 'Password cannot be one repeated character',
    passwordNumericSequence: 'Password cannot be a simple numeric sequence',
    passwordMismatch: 'Passwords do not match',
};

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
    const [emailTouched, setEmailTouched] = useState(false);
    const [passwordTouched, setPasswordTouched] = useState(false);
    const [confirmPasswordTouched, setConfirmPasswordTouched] = useState(false);
    const isEmailMode = !usernameOnly;
    const identifierValue = isEmailMode ? email : username;
    const identifierLabel = isEmailMode ? t('emailLabel') : t('usernameLabel');
    const identifierPrefix = isEmailMode ? 'email' : 'user';
    const identifierPlaceholder = isEmailMode ? 'user@cybervpn.io' : t('usernamePlaceholder');
    const identifierType = isEmailMode ? 'email' : 'text';
    const identifierAutocomplete = isEmailMode ? 'email' : 'username';
    const publicTermsUrl = `https://cyber-vpn.net/${locale}/terms`;
    const publicPrivacyUrl = `https://cyber-vpn.net/${locale}/privacy-policy`;

    const emailValidation = validateEmailInput(email, isEmailMode);
    const passwordValidation = validatePasswordInput(password);
    const passwordsMatch = password === confirmPassword && confirmPassword.length > 0;
    const passwordHasLayoutWarning = passwordValidation.codes.includes('passwordLatinLayout');
    const showEmailError = isEmailMode && emailTouched && !emailValidation.isValid;
    const showPasswordError = password.length > 0 && (!passwordValidation.isValid && (passwordTouched || passwordHasLayoutWarning));
    const showConfirmError = confirmPassword.length > 0 && (confirmPasswordTouched || password.length > 0) && !passwordsMatch;
    const hasRegistrationDraft = Boolean(username || email || password || confirmPassword);
    const canSubmit = usernameOnly
        ? username && passwordValidation.isValid && confirmPassword && acceptTerms && passwordsMatch && !isRateLimited
        : emailValidation.isValid && passwordValidation.isValid && confirmPassword && acceptTerms && passwordsMatch && !isRateLimited;
    const errorRef = useRef<HTMLDivElement>(null);

    const getValidationMessage = (code: EmailValidationCode | PasswordValidationCode | 'passwordMismatch') => {
        const key = `validation.${code}`;
        return t.has(key) ? t(key) : FALLBACK_VALIDATION_MESSAGES[code];
    };

    // Redirect existing authenticated users only before they start a new registration flow.
    useEffect(() => {
        if (isAuthenticated && !isLoading && !hasRegistrationDraft) {
            router.push(`/${locale}/dashboard`);
        }
    }, [hasRegistrationDraft, isAuthenticated, isLoading, router, locale]);

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
        setEmailTouched(true);
        setPasswordTouched(true);
        setConfirmPasswordTouched(true);
        if (!canSubmit) return;

        try {
            if (usernameOnly) {
                await register(username, password, { mode: 'username', tos_accepted: acceptTerms, marketing_consent: marketingConsent, locale });
                router.push(`/${locale}/login?registered=true`);
            } else {
                const normalizedEmail = normalizeEmailInput(email);
                await register(normalizedEmail, password, { mode: 'email', tos_accepted: acceptTerms, marketing_consent: marketingConsent, locale });
                router.push(`/${locale}/verify?email=${encodeURIComponent(normalizedEmail)}`);
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
            <form onSubmit={handleSubmit} className="keyboard-safe-bottom space-y-4" aria-busy={isLoading} noValidate>
                <div className="pt-1">
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
                        onBlur={() => {
                            if (isEmailMode) {
                                setEmailTouched(true);
                                setEmail((current) => normalizeEmailInput(current));
                            }
                        }}
                        required
                        inputMode={isEmailMode ? 'email' : 'text'}
                        autoComplete={identifierAutocomplete}
                        disabled={isLoading || isRateLimited}
                        error={showEmailError ? getValidationMessage(emailValidation.codes[0]) : undefined}
                        success={isEmailMode && emailTouched && emailValidation.isValid}
                        className="mobile-form-input"
                    />
                </div>

                <div className="space-y-2">
                    <CyberInput
                        label={t('passwordLabel')}
                        type="password"
                        prefix="pass"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        onBlur={() => setPasswordTouched(true)}
                        required
                        autoComplete="new-password"
                        disabled={isLoading || isRateLimited}
                        error={showPasswordError ? getValidationMessage(passwordValidation.codes[0]) : undefined}
                        success={password.length > 0 && passwordValidation.isValid}
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
                    onBlur={() => setConfirmPasswordTouched(true)}
                    required
                    autoComplete="new-password"
                    disabled={isLoading || isRateLimited}
                    error={showConfirmError ? getValidationMessage('passwordMismatch') : undefined}
                    success={passwordsMatch}
                    className="mobile-form-input"
                />

                <div className="space-y-2">
                    {/* Terms checkbox */}
                    <label className="flex cursor-pointer items-start gap-2 rounded-md py-1 group">
                        <div className="relative mt-0.5 shrink-0">
                            <input
                                type="checkbox"
                                checked={acceptTerms}
                                onChange={(e) => setAcceptTerms(e.target.checked)}
                                className="peer sr-only"
                                required
                                aria-label={t('acceptTerms')}
                            />
                            <div className="flex h-4 w-4 items-center justify-center rounded border border-grid-line bg-terminal-bg transition-all peer-checked:border-neon-cyan peer-checked:bg-neon-cyan peer-focus:ring-2 peer-focus:ring-neon-cyan/50">
                                {acceptTerms && <Check className="h-3 w-3 text-black" />}
                            </div>
                        </div>
                        <span className="text-xs text-muted-foreground font-mono leading-relaxed group-hover:text-foreground transition-colors">
                            {t('acceptTerms')}{' '}
                            <Link
                                href={publicTermsUrl}
                                prefetch={false}
                                className="inline-flex items-center text-neon-cyan hover:underline"
                            >
                                {t('termsLink')}
                            </Link>{' '}
                            {t('and')}{' '}
                            <Link
                                href={publicPrivacyUrl}
                                prefetch={false}
                                className="inline-flex items-center text-neon-cyan hover:underline"
                            >
                                {t('privacyLink')}
                            </Link>
                        </span>
                    </label>

                    {/* Marketing consent checkbox */}
                    <label className="flex cursor-pointer items-start gap-2 rounded-md py-1 group">
                        <div className="relative mt-0.5 shrink-0">
                            <input
                                type="checkbox"
                                checked={marketingConsent}
                                onChange={(e) => setMarketingConsent(e.target.checked)}
                                className="peer sr-only"
                                aria-label={t.has('marketingConsentLabel') ? t('marketingConsentLabel') : 'I want to receive marketing emails'}
                            />
                            <div className="flex h-4 w-4 items-center justify-center rounded border border-grid-line bg-terminal-bg transition-all peer-checked:border-neon-cyan peer-checked:bg-neon-cyan peer-focus:ring-2 peer-focus:ring-neon-cyan/50">
                                {marketingConsent && <Check className="h-3 w-3 text-black" />}
                            </div>
                        </div>
                        <span className="text-xs text-muted-foreground font-mono leading-relaxed group-hover:text-foreground transition-colors">
                            {t.has('marketingConsentLabel') ? t('marketingConsentLabel') : 'I want to receive news, special offers, and other updates'}
                        </span>
                    </label>
                </div>

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
            <p className="mt-4 text-center text-sm text-muted-foreground font-mono">
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
