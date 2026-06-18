'use client';

import { useState, useEffect, useRef } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { motion } from 'motion/react';
import { Fingerprint, LogIn, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link, useRouter } from '@/i18n/navigation';
import {
  AuthFormCard,
  CyberInput,
  CyberOtpInput,
  RateLimitCountdown,
  useIsRateLimited,
} from '@/features/auth/components';
import { ACCESS_DENIED_ERROR_CODE } from '@/features/auth/lib/partner-access';
import { isPasskeyWebAuthnError } from '@/features/auth/lib/passkey-webauthn';
import { completePendingTwoFactorSession } from '@/features/auth/lib/pending-twofa-client';
import { getSafeRedirectPath } from '@/features/auth/lib/redirect-path';
import {
  reportFrontendFormValidationError,
  reportFrontendSubmitAttempt,
  reportFrontendSubmitFailure,
} from '@/shared/lib/frontend-observability';
import { useAuthStore } from '@/stores/auth-store';

function getPasskeyErrorKey(error: unknown) {
  if (isPasskeyWebAuthnError(error)) {
    if (error.code === 'unsupported') {
      return 'passkeyUnsupported';
    }
    if (error.code === 'cancelled') {
      return 'passkeyCancelled';
    }
  }

  const axiosError = error as { response?: { data?: { detail?: unknown } } };
  const detail = axiosError.response?.data?.detail;
  const detailText = typeof detail === 'string'
    ? detail
    : typeof detail === 'object' && detail !== null
      ? JSON.stringify(detail)
      : '';
  const normalizedDetail = detailText.toLowerCase();

  if (normalizedDetail.includes('expired') || normalizedDetail.includes('challenge')) {
    return 'passkeyExpired';
  }

  return 'passkeyGenericError';
}

export function LoginClient() {
  const t = useTranslations('Auth.login');
  const locale = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectPath = getSafeRedirectPath(searchParams.get('redirect'), locale);

  const { login, loginWithPasskey, isLoading, error, isAuthenticated, clearError } = useAuthStore();
  const isRateLimited = useIsRateLimited();
  const isTwoFactorFlow = searchParams.get('2fa') === 'true';
  const accessDeniedError = searchParams.get('error') === ACCESS_DENIED_ERROR_CODE
    ? t('accessDenied')
    : null;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [twoFactorError, setTwoFactorError] = useState<string | null>(null);
  const [passkeyError, setPasskeyError] = useState<string | null>(null);
  const [isPasskeyLoading, setIsPasskeyLoading] = useState(false);
  const [isCompletingTwoFactor, setIsCompletingTwoFactor] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isAuthenticated) {
      router.push(redirectPath);
    }
  }, [isAuthenticated, redirectPath, router]);

  useEffect(() => {
    clearError();
    setPasskeyError(null);
  }, [clearError]);

  useEffect(() => {
    const activeError = passkeyError || twoFactorError || error || accessDeniedError;
    if (activeError && !isRateLimited && errorRef.current) {
      errorRef.current.focus();
    }
  }, [accessDeniedError, error, isRateLimited, passkeyError, twoFactorError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || isRateLimited) {
      reportFrontendFormValidationError('partner_portal', {
        errorCode: isRateLimited ? 'rate_limited' : 'missing_credentials',
        formName: 'login',
        path: window.location.pathname,
      });
      return;
    }

    try {
      reportFrontendSubmitAttempt('partner_portal', {
        formName: 'login',
        path: window.location.pathname,
      });
      await login(email, password);
    } catch (submitError) {
      reportFrontendSubmitFailure('partner_portal', {
        errorCode: submitError instanceof Error ? submitError.name || 'login_failed' : 'login_failed',
        formName: 'login',
        path: window.location.pathname,
      });
    }
  };

  const handlePasskeyLogin = async () => {
    if (isRateLimited) {
      reportFrontendFormValidationError('partner_portal', {
        errorCode: 'rate_limited',
        formName: 'login_passkey',
        path: window.location.pathname,
      });
      return;
    }

    setPasskeyError(null);
    setIsPasskeyLoading(true);

    try {
      reportFrontendSubmitAttempt('partner_portal', {
        formName: 'login_passkey',
        path: window.location.pathname,
      });
      await loginWithPasskey(email.trim() || undefined);
    } catch (submitError) {
      reportFrontendSubmitFailure('partner_portal', {
        errorCode: submitError instanceof Error ? submitError.name || 'passkey_login_failed' : 'passkey_login_failed',
        formName: 'login_passkey',
        path: window.location.pathname,
      });
      setPasskeyError(t(getPasskeyErrorKey(submitError)));
    } finally {
      setIsPasskeyLoading(false);
    }
  };

  const handleTwoFactorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (twoFactorCode.length !== 6) {
      reportFrontendFormValidationError('partner_portal', {
        errorCode: 'invalid_two_factor_code',
        formName: 'login_two_factor',
        path: window.location.pathname,
      });
      return;
    }

    setIsCompletingTwoFactor(true);
    setTwoFactorError(null);

    try {
      reportFrontendSubmitAttempt('partner_portal', {
        formName: 'login_two_factor',
        path: window.location.pathname,
      });
      const result = await completePendingTwoFactorSession(twoFactorCode);
      window.location.href = result.redirect_to;
    } catch (err) {
      reportFrontendSubmitFailure('partner_portal', {
        errorCode: err instanceof Error ? err.name || 'two_factor_failed' : 'two_factor_failed',
        formName: 'login_two_factor',
        path: window.location.pathname,
      });
      setTwoFactorError(err instanceof Error ? err.message : 'Two-factor verification failed.');
      setIsCompletingTwoFactor(false);
    }
  };

  return (
    <AuthFormCard title={t('title')} subtitle={t('subtitle')} className="keyboard-safe-bottom">
      <RateLimitCountdown />
      <div aria-live="assertive" aria-atomic="true">
        {(passkeyError || twoFactorError || error || accessDeniedError) && !isRateLimited && (
          <motion.div
            ref={errorRef}
            role="alert"
            tabIndex={-1}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-red-500/50"
          >
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{passkeyError || twoFactorError || error || accessDeniedError}</span>
          </motion.div>
        )}
      </div>
      {isTwoFactorFlow ? (
        <form onSubmit={handleTwoFactorSubmit} className="keyboard-safe-bottom space-y-5" aria-busy={isCompletingTwoFactor}>
          <p className="text-center text-sm font-mono text-muted-foreground">
            {t('twoFactorInfo')}
          </p>
          <div className="space-y-2">
            <label className="block text-sm font-mono text-muted-foreground">
              {t('twoFactorCodeLabel')}
            </label>
            <CyberOtpInput
              value={twoFactorCode}
              onChange={setTwoFactorCode}
              maxLength={6}
              error={Boolean(twoFactorError)}
              disabled={isCompletingTwoFactor}
              autoFocus
              ariaLabel={t('twoFactorCodeLabel')}
            />
          </div>
          <motion.div
            whileHover={{ scale: isCompletingTwoFactor ? 1 : 1.01 }}
            whileTap={{ scale: isCompletingTwoFactor ? 1 : 0.99 }}
            className="flex justify-center"
          >
            <Button
              type="submit"
              disabled={isCompletingTwoFactor || twoFactorCode.length !== 6}
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
        <form onSubmit={handleSubmit} className="keyboard-safe-bottom space-y-5" aria-busy={isLoading && !isPasskeyLoading}>
          <div className="space-y-3">
            <motion.div
              whileHover={{ scale: isLoading || isRateLimited ? 1 : 1.01 }}
              whileTap={{ scale: isLoading || isRateLimited ? 1 : 0.99 }}
              className="flex justify-center"
            >
              <Button
                type="button"
                onClick={handlePasskeyLogin}
                disabled={isLoading || isRateLimited}
                touchTarget="comfortable"
                className="min-w-[240px] h-12 border border-matrix-green/35 bg-matrix-green/10 text-matrix-green hover:bg-matrix-green/15 font-bold font-mono tracking-wider shadow-lg shadow-matrix-green/10 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label={isPasskeyLoading ? t('passkeyChecking') : t('passkeyButton')}
                aria-busy={isPasskeyLoading}
              >
                {isPasskeyLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    {t('passkeyChecking')}
                  </>
                ) : (
                  <>
                    <Fingerprint className="mr-2 h-4 w-4" aria-hidden="true" />
                    {t('passkeyButton')}
                  </>
                )}
              </Button>
            </motion.div>
            <p className="text-center text-xs font-mono leading-5 text-muted-foreground">
              {t('passkeyFallbackHint')}
            </p>
          </div>
          <CyberInput
            label={t('emailLabel')}
            type="email"
            prefix="email"
            placeholder={t('emailPlaceholder')}
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setPasskeyError(null);
            }}
            required
            autoComplete="username webauthn"
            disabled={isLoading || isRateLimited}
            className="mobile-form-input"
          />
          <CyberInput
            label={t('passwordLabel')}
            type="password"
            prefix="pass"
            placeholder={t('passwordPlaceholder')}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            disabled={isLoading || isRateLimited}
            className="mobile-form-input"
          />
          <div className="flex justify-end">
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
          {searchParams.get('registered') === 'true' && !error && (
            <motion.div
              role="status"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 flex items-center gap-2 rounded-lg border border-matrix-green/20 bg-matrix-green/10 p-3 text-sm font-mono text-matrix-green"
            >
              <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{t('registeredNotice')}</span>
            </motion.div>
          )}
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
