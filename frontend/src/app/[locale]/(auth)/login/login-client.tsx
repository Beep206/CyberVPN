'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useSearchParams, useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import Link from 'next/link';
import { LogIn, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authAnalytics } from '@/lib/analytics';
import {
  AuthFormCard,
  CyberInput,
  SocialAuthButtons,
  AuthDivider,
  RateLimitCountdown,
  useIsRateLimited,
} from '@/features/auth/components';
import {
  getOAuthErrorMessageKey,
  getOAuthFailureKind,
  isOAuthProvider,
  OAUTH_PROVIDER_QUERY_PARAM,
} from '@/features/auth/lib/oauth-error-codes';
import { completePendingTwoFactorSession } from '@/features/auth/lib/pending-twofa-client';
import { getSafeRedirectPath } from '@/features/auth/lib/redirect-path';
import { useAuthStore } from '@/stores/auth-store';

export function LoginClient() {
  const t = useTranslations('Auth.login');
  const router = useRouter();
  const locale = useLocale();
  const searchParams = useSearchParams();
  const redirectPath = getSafeRedirectPath(searchParams.get('redirect'), locale);

  const { login, oauthLogin, isLoading, error, isAuthenticated, clearError } = useAuthStore();
  const isRateLimited = useIsRateLimited();
  const isTwoFactorFlow = searchParams.get('2fa') === 'true';
  const oauthErrorCode = searchParams.get('oauth_error');
  const rawOAuthProvider = searchParams.get(OAUTH_PROVIDER_QUERY_PARAM);
  const oauthProvider = isOAuthProvider(rawOAuthProvider) ? rawOAuthProvider : null;
  const oauthErrorMessage = oauthErrorCode
    ? t(getOAuthErrorMessageKey(oauthErrorCode) as never)
    : null;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [twoFactorError, setTwoFactorError] = useState<string | null>(null);
  const [isCompletingTwoFactor, setIsCompletingTwoFactor] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);
  const trackedOAuthEventRef = useRef<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      router.push(redirectPath);
    }
  }, [isAuthenticated, redirectPath, router, locale]);

  useEffect(() => {
    clearError();
  }, [clearError]);

  useEffect(() => {
    const activeError = twoFactorError || oauthErrorMessage || error;
    if (activeError && !isRateLimited && errorRef.current) {
      errorRef.current.focus();
    }
  }, [error, isRateLimited, oauthErrorMessage, twoFactorError]);

  useEffect(() => {
    if (!oauthProvider) {
      return;
    }

    const trackingKey = `${oauthProvider}:${oauthErrorCode ?? 'none'}:${isTwoFactorFlow ? '2fa' : 'default'}`;
    if (trackedOAuthEventRef.current === trackingKey) {
      return;
    }
    trackedOAuthEventRef.current = trackingKey;

    if (oauthErrorCode) {
      switch (getOAuthFailureKind(oauthErrorCode)) {
        case 'provider_denied':
          authAnalytics.oauthProviderDenied(oauthProvider);
          break;
        case 'collision':
          authAnalytics.oauthCollision(oauthProvider, oauthErrorCode);
          break;
        default:
          authAnalytics.oauthCallbackFailed(oauthProvider, oauthErrorCode);
      }
      return;
    }

    if (isTwoFactorFlow) {
      authAnalytics.oauthTwoFactorRequired(oauthProvider);
    }
  }, [isTwoFactorFlow, oauthErrorCode, oauthProvider]);

  const handleOAuthLogin = (provider: string) => {
    oauthLogin(provider as Parameters<typeof oauthLogin>[0]).catch(() => {});
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(email, password, rememberMe);
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
      <SocialAuthButtons onProviderClick={handleOAuthLogin} disabled={isLoading || isRateLimited} />
      <AuthDivider text={t('divider')} />
      <RateLimitCountdown />
      <div aria-live="assertive" aria-atomic="true">
        {(twoFactorError || oauthErrorMessage || error) && !isRateLimited && (
          <motion.div
            ref={errorRef}
            role="alert"
            tabIndex={-1}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-red-500/50"
          >
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{twoFactorError || oauthErrorMessage || error}</span>
          </motion.div>
        )}
        {searchParams.get('registered') === 'true' && !error && (
          <motion.div
            role="status"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm font-mono"
          >
            <Loader2 className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>Registration successful! Please check your email for activation instructions.</span>
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
          <div className="flex items-center justify-between text-sm">
            <label className="touch-target flex items-center gap-2 cursor-pointer group">
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
              className="touch-target inline-flex items-center text-neon-cyan hover:text-neon-cyan/80 font-mono text-xs transition-colors"
            >
              {t('forgotPassword')}
            </Link>
          </div>
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
      {!isTwoFactorFlow && (
        <>
          <p className="mt-4 text-center text-sm text-muted-foreground font-mono">
            <Link
              href="/magic-link"
              className="touch-target inline-flex items-center text-neon-cyan hover:text-neon-cyan/80 transition-colors underline underline-offset-4"
            >
              {t('magicLinkAlt') ?? 'Sign in with magic link'}
            </Link>
          </p>
          <p className="mt-4 text-center text-sm text-muted-foreground font-mono">
            {t('noAccount')}{' '}
            <Link
              href="/register"
              className="touch-target inline-flex items-center text-neon-purple hover:text-neon-purple/80 transition-colors underline underline-offset-4"
            >
              {t('signUpLink')}
            </Link>
          </p>
        </>
      )}
    </AuthFormCard>
  );
}
