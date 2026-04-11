'use client';

import { useState, useEffect, useRef } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useSearchParams, useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import { LogIn, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  AuthFormCard,
  CyberInput,
  RateLimitCountdown,
  useIsRateLimited,
} from '@/features/auth/components';
import { ACCESS_DENIED_ERROR_CODE } from '@/features/auth/lib/admin-access';
import { completePendingTwoFactorSession } from '@/features/auth/lib/pending-twofa-client';
import { getSafeRedirectPath } from '@/features/auth/lib/redirect-path';
import { useAuthStore } from '@/stores/auth-store';

export function LoginClient() {
  const t = useTranslations('Auth.login');
  const locale = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectPath = getSafeRedirectPath(searchParams.get('redirect'), locale);

  const { login, isLoading, error, isAuthenticated, clearError } = useAuthStore();
  const isRateLimited = useIsRateLimited();
  const isTwoFactorFlow = searchParams.get('2fa') === 'true';
  const accessDeniedError = searchParams.get('error') === ACCESS_DENIED_ERROR_CODE
    ? locale === 'ru-RU'
      ? 'Доступ запрещён. Требуется аккаунт администратора.'
      : 'Access denied. Administrator account required.'
    : null;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [twoFactorError, setTwoFactorError] = useState<string | null>(null);
  const [isCompletingTwoFactor, setIsCompletingTwoFactor] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isAuthenticated) {
      router.push(redirectPath);
    }
  }, [isAuthenticated, redirectPath, router]);

  useEffect(() => {
    clearError();
  }, [clearError]);

  useEffect(() => {
    const activeError = twoFactorError || error || accessDeniedError;
    if (activeError && !isRateLimited && errorRef.current) {
      errorRef.current.focus();
    }
  }, [accessDeniedError, error, isRateLimited, twoFactorError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(email, password);
    } catch {}
  };

  const handleTwoFactorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCompletingTwoFactor(true);
    setTwoFactorError(null);

    try {
      const result = await completePendingTwoFactorSession(twoFactorCode);
      window.location.href = result.redirect_to;
    } catch (err) {
      setTwoFactorError(err instanceof Error ? err.message : 'Two-factor verification failed.');
      setIsCompletingTwoFactor(false);
    }
  };

  return (
    <AuthFormCard title={t('title')} subtitle={t('subtitle')} className="keyboard-safe-bottom">
      <RateLimitCountdown />
      <div aria-live="assertive" aria-atomic="true">
        {(twoFactorError || error || accessDeniedError) && !isRateLimited && (
          <motion.div
            ref={errorRef}
            role="alert"
            tabIndex={-1}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-red-500/50"
          >
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{twoFactorError || error || accessDeniedError}</span>
          </motion.div>
        )}
      </div>
      {isTwoFactorFlow ? (
        <form onSubmit={handleTwoFactorSubmit} className="keyboard-safe-bottom space-y-5" aria-busy={isCompletingTwoFactor}>
          <p className="text-center text-sm font-mono text-muted-foreground">
            {t('twoFactorInfo')}
          </p>
          <CyberInput
            label={t('twoFactorCodeLabel')}
            type="text"
            prefix="2fa"
            placeholder={t('twoFactorCodePlaceholder')}
            value={twoFactorCode}
            onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            required
            autoComplete="one-time-code"
            disabled={isCompletingTwoFactor}
            className="mobile-form-input"
          />
          <motion.div
            whileHover={{ scale: isCompletingTwoFactor ? 1 : 1.01 }}
            whileTap={{ scale: isCompletingTwoFactor ? 1 : 0.99 }}
            className="flex justify-center"
          >
            <Button
              type="submit"
              disabled={isCompletingTwoFactor}
              touchTarget="comfortable"
              className="min-w-[200px] h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label={isCompletingTwoFactor ? t('twoFactorSubmitting') : t('twoFactorSubmitButton')}
            >
              {isCompletingTwoFactor ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('twoFactorSubmitting')}
                </>
              ) : (
                <>
                  <LogIn className="mr-2 h-4 w-4" />
                  {t('twoFactorSubmitButton')}
                </>
              )}
            </Button>
          </motion.div>
        </form>
      ) : (
        <form onSubmit={handleSubmit} className="keyboard-safe-bottom space-y-5" aria-busy={isLoading}>
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
            className="mobile-form-input"
          />
          <CyberInput
            label={t('passwordLabel')}
            type="password"
            prefix="pass"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            disabled={isLoading || isRateLimited}
            className="mobile-form-input"
          />
          <motion.div
            whileHover={{ scale: isLoading || isRateLimited ? 1 : 1.01 }}
            whileTap={{ scale: isLoading || isRateLimited ? 1 : 0.99 }}
            className="flex justify-center"
          >
            <Button
              type="submit"
              disabled={isLoading || isRateLimited}
              touchTarget="comfortable"
              className="min-w-[200px] h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label={isLoading ? t('submitting') : t('submitButton')}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('submitting')}
                </>
              ) : (
                <>
                  <LogIn className="mr-2 h-4 w-4" />
                  {t('submitButton')}
                </>
              )}
            </Button>
          </motion.div>
        </form>
      )}
    </AuthFormCard>
  );
}
