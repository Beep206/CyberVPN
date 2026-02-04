'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { useRouter } from '@/i18n/navigation';
import { motion } from 'motion/react';
import Link from 'next/link';
import { LogIn, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    AuthFormCard,
    CyberInput,
    SocialAuthButtons,
    AuthDivider,
    RateLimitCountdown,
    useIsRateLimited,
} from '@/features/auth/components';
import { useAuthStore } from '@/stores/auth-store';

export default function LoginPage() {
    const t = useTranslations('Auth.login');
    const router = useRouter();
    const searchParams = useSearchParams();
    const redirectPath = searchParams.get('redirect') || '/dashboard';

    const { login, isLoading, error, isAuthenticated, clearError } = useAuthStore();
    const isRateLimited = useIsRateLimited();

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);
    const errorRef = useRef<HTMLDivElement>(null);

    // Redirect if already authenticated
    useEffect(() => {
        if (isAuthenticated) {
            // Validate redirect URL for security - only allow relative paths
            const isValidRedirect = redirectPath.startsWith('/') && !redirectPath.startsWith('//');
            router.push(isValidRedirect ? redirectPath : '/dashboard');
        }
    }, [isAuthenticated, redirectPath, router]);

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
        try {
            await login(email, password, rememberMe);
            // Redirect handled by useEffect above
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

            {/* Login form */}
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
                    disabled={isLoading || isRateLimited}
                />

                <CyberInput
                    label={t('password')}
                    type="password"
                    prefix="pass"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    disabled={isLoading || isRateLimited}
                />

                {/* Remember me & Forgot password */}
                <div className="flex items-center justify-between text-sm">
                    <label className="flex items-center gap-2 cursor-pointer group">
                        <input
                            type="checkbox"
                            checked={rememberMe}
                            onChange={(e) => setRememberMe(e.target.checked)}
                            className="w-4 h-4 rounded border-grid-line bg-terminal-bg checked:bg-neon-cyan checked:border-neon-cyan focus:ring-neon-cyan/50 focus:ring-2 transition-colors cursor-pointer"
                            aria-label={t('rememberMe')}
                        />
                        <span className="text-muted-foreground font-mono text-xs group-hover:text-foreground transition-colors">
                            {t('rememberMe')}
                        </span>
                    </label>

                    <Link
                        href="/forgot-password"
                        className="text-neon-cyan hover:text-neon-cyan/80 font-mono text-xs transition-colors"
                    >
                        {t('forgotPassword')}
                    </Link>
                </div>

                {/* Submit button */}
                <motion.div
                    whileHover={{ scale: isLoading || isRateLimited ? 1 : 1.01 }}
                    whileTap={{ scale: isLoading || isRateLimited ? 1 : 0.99 }}
                >
                    <Button
                        type="submit"
                        disabled={isLoading || isRateLimited}
                        className="w-full h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        aria-label={isLoading ? t('authenticating') : t('submit')}
                    >
                        {isLoading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                {t('authenticating')}
                            </>
                        ) : (
                            <>
                                <LogIn className="mr-2 h-4 w-4" />
                                {t('submit')}
                            </>
                        )}
                    </Button>
                </motion.div>
            </form>

            {/* Register link */}
            <p className="mt-6 text-center text-sm text-muted-foreground font-mono">
                {t('noAccount')}{' '}
                <Link
                    href="/register"
                    className="text-neon-purple hover:text-neon-purple/80 transition-colors underline underline-offset-4"
                >
                    {t('createAccount')}
                </Link>
            </p>
        </AuthFormCard>
    );
}
