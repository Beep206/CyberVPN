'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import Link from 'next/link';
import { UserPlus, Loader2, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    AuthFormCard,
    CyberInput,
    SocialAuthButtons,
    AuthDivider,
    PasswordStrengthMeter,
} from '@/features/auth/components';

export default function RegisterPage() {
    const t = useTranslations('Auth.register');
    const [isLoading, setIsLoading] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [acceptTerms, setAcceptTerms] = useState(false);

    const passwordsMatch = password === confirmPassword && confirmPassword.length > 0;
    const canSubmit = email && password && confirmPassword && acceptTerms && passwordsMatch;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!canSubmit) return;

        setIsLoading(true);
        // Simulate API call
        await new Promise((resolve) => setTimeout(resolve, 1500));
        setIsLoading(false);
    };

    return (
        <AuthFormCard
            title={t('title')}
            subtitle={t('subtitle')}
        >
            {/* Social auth */}
            <SocialAuthButtons disabled={isLoading} />

            <AuthDivider text={t('divider')} />

            {/* Register form */}
            <form onSubmit={handleSubmit} className="space-y-5">
                <CyberInput
                    label={t('email')}
                    type="email"
                    prefix="email"
                    placeholder="user@cybervpn.io"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    disabled={isLoading}
                />

                <div className="space-y-2">
                    <CyberInput
                        label={t('password')}
                        type="password"
                        prefix="pass"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        autoComplete="new-password"
                        disabled={isLoading}
                    />
                    <PasswordStrengthMeter password={password} />
                </div>

                <CyberInput
                    label={t('confirmPassword')}
                    type="password"
                    prefix="confirm"
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    disabled={isLoading}
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
                >
                    <Button
                        type="submit"
                        disabled={isLoading || !canSubmit}
                        className="w-full h-12 bg-neon-purple hover:bg-neon-purple/90 text-white font-bold font-mono tracking-wider shadow-lg shadow-neon-purple/20 hover:shadow-neon-purple/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                    >
                        {isLoading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                {t('creating')}
                            </>
                        ) : (
                            <>
                                <UserPlus className="mr-2 h-4 w-4" />
                                {t('submit')}
                            </>
                        )}
                    </Button>
                </motion.div>
            </form>

            {/* Login link */}
            <p className="mt-6 text-center text-sm text-muted-foreground font-mono">
                {t('haveAccount')}{' '}
                <Link
                    href="/login"
                    className="text-neon-cyan hover:text-neon-cyan/80 transition-colors underline underline-offset-4"
                >
                    {t('signIn')}
                </Link>
            </p>
        </AuthFormCard>
    );
}
