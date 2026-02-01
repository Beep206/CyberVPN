'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import Link from 'next/link';
import { LogIn, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    AuthFormCard,
    CyberInput,
    SocialAuthButtons,
    AuthDivider,
} from '@/features/auth/components';

export default function LoginPage() {
    const t = useTranslations('Auth.login');
    const [isLoading, setIsLoading] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
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
                    disabled={isLoading}
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
                    disabled={isLoading}
                />

                {/* Remember me & Forgot password */}
                <div className="flex items-center justify-between text-sm">
                    <label className="flex items-center gap-2 cursor-pointer group">
                        <input
                            type="checkbox"
                            checked={rememberMe}
                            onChange={(e) => setRememberMe(e.target.checked)}
                            className="w-4 h-4 rounded border-grid-line bg-terminal-bg checked:bg-neon-cyan checked:border-neon-cyan focus:ring-neon-cyan/50 focus:ring-2 transition-colors cursor-pointer"
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
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                >
                    <Button
                        type="submit"
                        disabled={isLoading}
                        className="w-full h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all cursor-pointer"
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
