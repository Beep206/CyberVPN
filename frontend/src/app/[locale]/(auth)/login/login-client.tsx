'use client';

import { useCallback, useState, useEffect, useRef } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useSearchParams, useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import Link from 'next/link';
import { LogIn, Loader2, AlertCircle, Fingerprint } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authAnalytics } from '@/lib/analytics';
import { passkeysApi, type PasskeyPolicyResponse } from '@/lib/api';
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
import {
  completePendingTwoFactorSession,
  getPendingTwoFactorSession,
  stagePendingTwoFactorSession,
} from '@/features/auth/lib/pending-twofa-client';
import {
  cancelPasskeyCeremony,
  completePasskeyAuthentication,
  getPasskeyBrowserSupport,
  getPasskeyErrorMessageKey,
  type PasskeyBrowserSupport,
} from '@/features/auth/lib/passkey-webauthn';
import { getCanonicalPostLoginHref, getSafeRedirectPath } from '@/features/auth/lib/redirect-path';
import {
  validateLoginIdentifierInput,
  type LoginIdentifierValidationCode,
} from '@/features/auth/lib/validation';
import { useAuthStore } from '@/stores/auth-store';

const FALLBACK_LOGIN_VALIDATION_MESSAGES: Record<LoginIdentifierValidationCode, string> = {
  loginIdentifierRequired: 'Email or username is required',
  emailRequired: 'Email is required',
  emailInvalid: 'Enter a valid email address',
  emailNoSpaces: 'Email must not contain spaces',
  emailTooLong: 'Email is too long',
};

type TwoFactorSessionState = 'idle' | 'checking' | 'ready' | 'expired';
type PasskeyActionState = 'idle' | 'checking';

export function LoginClient() {
  const t = useTranslations('Auth.login');
  const router = useRouter();
  const locale = useLocale();
  const searchParams = useSearchParams();
  const redirectPath = getSafeRedirectPath(searchParams.get('redirect'), locale);

  const { login, oauthLogin, fetchUser, isLoading, error, isAuthenticated, clearError } = useAuthStore();
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
  const [identifierTouched, setIdentifierTouched] = useState(false);
  const [passkeyActionState, setPasskeyActionState] = useState<PasskeyActionState>('idle');
  const [passkeyError, setPasskeyError] = useState<string | null>(null);
  const [passkeyPolicy, setPasskeyPolicy] = useState<PasskeyPolicyResponse | null>(null);
  const [passkeySupport, setPasskeySupport] = useState<PasskeyBrowserSupport | null>(null);
  const [twoFactorSessionState, setTwoFactorSessionState] = useState<TwoFactorSessionState>(
    isTwoFactorFlow ? 'checking' : 'idle',
  );
  const errorRef = useRef<HTMLDivElement>(null);
  const loginIdentifierInputRef = useRef<HTMLInputElement>(null);
  const twoFactorInputRef = useRef<HTMLInputElement>(null);
  const trackedOAuthEventRef = useRef<string | null>(null);
  const conditionalPasskeyStartedRef = useRef(false);
  const loginIdentifierValidation = validateLoginIdentifierInput(email);

  const getLoginIdentifierValidationMessage = (code: LoginIdentifierValidationCode): string => {
    const key = `validation.${code}`;
    return t.has(key) ? t(key) : FALLBACK_LOGIN_VALIDATION_MESSAGES[code];
  };

  const loginIdentifierError = identifierTouched && !loginIdentifierValidation.isValid
    ? getLoginIdentifierValidationMessage(loginIdentifierValidation.codes[0])
    : undefined;
  const passkeyAvailable = Boolean(
    passkeyPolicy?.enabled &&
    passkeyPolicy.authenticationEnabled &&
    passkeySupport?.secureContext &&
    passkeySupport.webAuthn,
  );
  const passkeyUnsupported = Boolean(
    passkeyPolicy?.enabled &&
    passkeySupport &&
    (!passkeySupport.secureContext || !passkeySupport.webAuthn),
  );
  const hasPasskeyEntryPoint = !isTwoFactorFlow && (passkeyAvailable || passkeyUnsupported);
  const passkeyInputAutocomplete =
    passkeyPolicy?.conditionalUiEnabled && passkeySupport?.autofill && passkeyAvailable
      ? 'username webauthn'
      : 'username';

  const navigateAfterAuth = useCallback((targetPath: string) => {
    const canonicalHref = typeof window === 'undefined'
      ? null
      : getCanonicalPostLoginHref(targetPath, window.location);

    if (canonicalHref) {
      window.location.assign(canonicalHref);
      return;
    }

    router.push(targetPath);
  }, [router]);

  useEffect(() => {
    if (isAuthenticated) {
      navigateAfterAuth(redirectPath);
    }
  }, [isAuthenticated, navigateAfterAuth, redirectPath]);

  useEffect(() => {
    clearError();
  }, [clearError]);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      passkeysApi
        .getPolicy()
        .then((response) => response.data)
        .catch(() => null),
      getPasskeyBrowserSupport(),
    ]).then(([policy, support]) => {
      if (cancelled) {
        return;
      }

      setPasskeyPolicy(policy);
      setPasskeySupport(support);
    });

    return () => {
      cancelled = true;
      cancelPasskeyCeremony();
    };
  }, []);

  useEffect(() => {
    if (!isTwoFactorFlow) {
      return;
    }

    let cancelled = false;

    getPendingTwoFactorSession()
      .then((session) => {
        if (cancelled) {
          return;
        }

        if (!session.pending) {
          setTwoFactorSessionState('expired');
          setTwoFactorError(t('twoFactorSessionExpired'));
          return;
        }

        setTwoFactorSessionState('ready');
        setTwoFactorError(null);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        setTwoFactorSessionState('expired');
        setTwoFactorError(t('twoFactorSessionCheckFailed'));
      });

    return () => {
      cancelled = true;
    };
  }, [isTwoFactorFlow, t]);

  useEffect(() => {
    if (twoFactorSessionState === 'ready') {
      twoFactorInputRef.current?.focus();
    }
  }, [twoFactorSessionState]);

  useEffect(() => {
    const activeError = twoFactorError || passkeyError || oauthErrorMessage || error;
    if (activeError && !isRateLimited && errorRef.current) {
      errorRef.current.focus();
    }
  }, [error, isRateLimited, oauthErrorMessage, passkeyError, twoFactorError]);

  useEffect(() => {
    if (
      isTwoFactorFlow ||
      conditionalPasskeyStartedRef.current ||
      !passkeyPolicy?.enabled ||
      !passkeyPolicy.authenticationEnabled ||
      !passkeyPolicy.conditionalUiEnabled ||
      !passkeySupport?.secureContext ||
      !passkeySupport.autofill ||
      !passkeySupport.webAuthn
    ) {
      return;
    }

    let cancelled = false;
    conditionalPasskeyStartedRef.current = true;

    completePasskeyAuthentication({
      conditional: true,
      identifier: null,
    })
      .then(async ({ data }) => {
        if (cancelled) {
          return;
        }

        if (data.requires_2fa && data.tfa_token) {
          setTwoFactorSessionState('checking');
          await stagePendingTwoFactorSession({
            token: data.tfa_token,
            locale,
            returnTo: redirectPath,
          });
          router.push(`/${locale}/login?2fa=true`);
          return;
        }

        if (data.requires_2fa && !data.tfa_token) {
          setPasskeyError(t('twoFactorStartFailed'));
          return;
        }

        await fetchUser();
        navigateAfterAuth(redirectPath);
      })
      .catch((err) => {
        if (cancelled) {
          return;
        }

        const messageKey = getPasskeyErrorMessageKey(err);
        if (messageKey !== 'passkeyCancelled') {
          setPasskeyError(t(messageKey as never));
        }
      });

    return () => {
      cancelled = true;
      cancelPasskeyCeremony();
    };
  }, [fetchUser, isTwoFactorFlow, locale, navigateAfterAuth, passkeyPolicy, passkeySupport, redirectPath, router, t]);

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

  const handlePasskeyLogin = async () => {
    setPasskeyError(null);

    if (!passkeyAvailable) {
      setPasskeyError(t('passkeyUnsupported'));
      return;
    }

    setPasskeyActionState('checking');
    cancelPasskeyCeremony();

    try {
      const currentIdentifier = loginIdentifierInputRef.current?.value ?? email;
      const { data } = await completePasskeyAuthentication({
        conditional: false,
        identifier: currentIdentifier,
      });

      if (data.requires_2fa && data.tfa_token) {
        setTwoFactorSessionState('checking');
        await stagePendingTwoFactorSession({
          token: data.tfa_token,
          locale,
          returnTo: redirectPath,
        });
        router.push(`/${locale}/login?2fa=true`);
        return;
      }

      if (data.requires_2fa && !data.tfa_token) {
        setPasskeyError(t('twoFactorStartFailed'));
        return;
      }

      await fetchUser();
      navigateAfterAuth(redirectPath);
    } catch (err) {
      setPasskeyError(t(getPasskeyErrorMessageKey(err) as never));
    } finally {
      setPasskeyActionState('idle');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTwoFactorError(null);
    setIdentifierTouched(true);

    const currentIdentifierValidation = validateLoginIdentifierInput(email);
    if (!currentIdentifierValidation.isValid) {
      return;
    }

    try {
      const result = await login(email.trim(), password, rememberMe);
      if (result.requires_2fa && result.tfa_token) {
        setTwoFactorSessionState('checking');
        await stagePendingTwoFactorSession({
          token: result.tfa_token,
          locale,
          returnTo: redirectPath,
        });
        router.push(`/${locale}/login?2fa=true`);
        return;
      }
      if (result.requires_2fa && !result.tfa_token) {
        setTwoFactorError(t('twoFactorStartFailed'));
        return;
      }
      navigateAfterAuth(redirectPath);
    } catch {}
  };

  const handleTwoFactorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (twoFactorSessionState !== 'ready') {
      setTwoFactorError(t('twoFactorSessionExpired'));
      return;
    }

    setIsCompletingTwoFactor(true);
    setTwoFactorError(null);

    try {
      const result = await completePendingTwoFactorSession(twoFactorCode);
      window.location.href = result.redirect_to;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Two-factor verification failed.';
      setTwoFactorError(message);
      if (/session expired|start sign-in/i.test(message)) {
        setTwoFactorSessionState('expired');
      }
      setIsCompletingTwoFactor(false);
    }
  };

  return (
    <AuthFormCard title={t('title')} subtitle={t('subtitle')} className="keyboard-safe-bottom">
      {hasPasskeyEntryPoint && (
        <div className="space-y-2">
          {passkeyAvailable ? (
            <motion.div
              whileHover={{ scale: passkeyActionState === 'checking' ? 1 : 1.01 }}
              whileTap={{ scale: passkeyActionState === 'checking' ? 1 : 0.99 }}
              className="flex justify-center"
            >
              <Button
                type="button"
                disabled={passkeyActionState === 'checking' || isRateLimited}
                touchTarget="comfortable"
                onClick={() => void handlePasskeyLogin()}
                className="min-h-12 w-full border border-matrix-green/40 bg-matrix-green/10 font-mono font-bold tracking-wider text-matrix-green shadow-lg shadow-matrix-green/10 transition-all hover:bg-matrix-green/15 hover:shadow-matrix-green/20 disabled:cursor-not-allowed disabled:opacity-50"
                aria-label={passkeyActionState === 'checking' ? t('passkeyChecking') : t('passkeyButton')}
                aria-busy={passkeyActionState === 'checking'}
              >
                {passkeyActionState === 'checking' ? (
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
          ) : (
            <p role="status" className="rounded-lg border border-grid-line/40 bg-terminal-bg/60 p-3 text-center font-mono text-xs text-muted-foreground">
              {t('passkeyUnsupported')} {t('passkeyFallbackHint')}
            </p>
          )}
        </div>
      )}
      <SocialAuthButtons
        onProviderClick={handleOAuthLogin}
        disabled={isLoading || isRateLimited}
        className={hasPasskeyEntryPoint ? 'mt-4 sm:mt-5' : undefined}
      />
      <AuthDivider text={t('divider')} />
      <RateLimitCountdown />
      <div aria-live="assertive" aria-atomic="true">
        {(twoFactorError || passkeyError || oauthErrorMessage || error) && !isRateLimited && (
          <motion.div
            ref={errorRef}
            role="alert"
            tabIndex={-1}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-red-500/50"
          >
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{twoFactorError || passkeyError || oauthErrorMessage || error}</span>
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
          {twoFactorSessionState === 'checking' && (
            <p role="status" className="text-center text-sm font-mono text-muted-foreground">
              {t('twoFactorChecking')}
            </p>
          )}

          {twoFactorSessionState === 'expired' ? (
            <div className="flex justify-center">
              <Link
                href={`/${locale}/login`}
                className="inline-flex min-h-11 items-center justify-center rounded-lg border border-neon-cyan/40 px-4 text-sm font-mono text-neon-cyan transition-colors hover:border-neon-cyan hover:text-neon-cyan/80"
              >
                {t('twoFactorStartOver')}
              </Link>
            </div>
          ) : twoFactorSessionState === 'ready' ? (
            <>
              <p className="text-center text-sm font-mono text-muted-foreground">
                {t('twoFactorInfo')}
              </p>
              <CyberInput
                ref={twoFactorInputRef}
                label={t('twoFactorCodeLabel')}
                type="text"
                inputMode="numeric"
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
            </>
          ) : null}
        </form>
      ) : (
        <form onSubmit={handleSubmit} className="keyboard-safe-bottom space-y-5" aria-busy={isLoading}>
          <CyberInput
            ref={loginIdentifierInputRef}
            label={t('emailLabel')}
            type="text"
            prefix="email"
            placeholder={t('emailPlaceholder')}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={() => setIdentifierTouched(true)}
            error={loginIdentifierError}
            success={identifierTouched && loginIdentifierValidation.isValid && email.trim().length > 0}
            required
            autoComplete={passkeyInputAutocomplete}
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
        <div className="mt-3 space-y-2 text-center text-sm text-muted-foreground font-mono">
          <p>
            <Link
              href="/magic-link"
              className="inline-flex items-center text-neon-cyan hover:text-neon-cyan/80 transition-colors underline underline-offset-4"
            >
              {t('magicLinkAlt') ?? 'Sign in with magic link'}
            </Link>
          </p>
          <p>
            {t('noAccount')}{' '}
            <Link
              href="/register"
              className="inline-flex items-center text-neon-purple hover:text-neon-purple/80 transition-colors underline underline-offset-4"
            >
              {t('signUpLink')}
            </Link>
          </p>
        </div>
      )}
    </AuthFormCard>
  );
}
