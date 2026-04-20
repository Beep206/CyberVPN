'use client';

import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { AlertCircle, Loader2, MailCheck, RefreshCw } from 'lucide-react';
import { AxiosError } from 'axios';
import { Button } from '@/components/ui/button';
import { Link, useRouter } from '@/i18n/navigation';
import { AuthFormCard, CyberOtpInput } from '@/features/auth/components';
import { authApi, type OtpErrorResponse } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth-store';

export function VerifyClient() {
  const t = useTranslations('Auth.verify');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { verifyOtpAndLogin, isLoading, error, clearError } = useAuthStore();

  const email = searchParams.get('email') ?? '';
  const [code, setCode] = useState('');
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null);
  const [resendsRemaining, setResendsRemaining] = useState<number | null>(null);
  const [isResending, setIsResending] = useState(false);
  const [resendCountdown, setResendCountdown] = useState(30);
  const [localError, setLocalError] = useState<string | null>(null);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    clearError();
  }, [clearError]);

  useEffect(() => {
    if (resendCountdown <= 0) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setResendCountdown((current) => Math.max(0, current - 1));
    }, 1000);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [resendCountdown]);

  useEffect(() => {
    if ((error || localError) && errorRef.current) {
      errorRef.current.focus();
    }
  }, [error, localError]);

  const handleVerify = async () => {
    if (code.length !== 6 || !email) {
      return;
    }

    setLocalError(null);
    setAttemptsRemaining(null);

    try {
      await verifyOtpAndLogin(email, code);
      router.push('/application');
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: OtpErrorResponse | string }>;
      const detail = axiosError.response?.data?.detail;

      if (typeof detail === 'object' && detail !== null) {
        setLocalError(detail.detail || t('invalidCode'));
        setAttemptsRemaining(detail.attempts_remaining ?? null);
      } else if (typeof detail === 'string') {
        setLocalError(detail);
      } else if (err instanceof Error) {
        setLocalError(err.message);
      } else {
        setLocalError(t('invalidCode'));
      }
      setCode('');
    }
  };

  const handleResend = async () => {
    if (!email || resendCountdown > 0 || isResending) {
      return;
    }

    setIsResending(true);
    setLocalError(null);

    try {
      const response = await authApi.resendOtp({ email });
      setResendsRemaining(response.data.resends_remaining);
      setResendCountdown(60);
      setCode('');
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: OtpErrorResponse | string }>;
      const detail = axiosError.response?.data?.detail;

      if (typeof detail === 'object' && detail !== null) {
        setLocalError(detail.detail || t('resendFailed'));
      } else if (typeof detail === 'string') {
        setLocalError(detail);
      } else {
        setLocalError(t('resendFailed'));
      }
    } finally {
      setIsResending(false);
    }
  };

  if (!email) {
    return (
      <AuthFormCard title={t('title')} subtitle={t('missingEmail')}>
        <div className="space-y-5 text-center">
          <AlertCircle className="mx-auto h-10 w-10 text-neon-pink" aria-hidden="true" />
          <p className="text-sm font-mono text-muted-foreground">{t('missingEmail')}</p>
          <Link
            href="/register"
            className="inline-flex items-center justify-center text-sm font-mono text-neon-cyan underline underline-offset-4"
          >
            {t('goToRegister')}
          </Link>
        </div>
      </AuthFormCard>
    );
  }

  return (
    <AuthFormCard title={t('title')} subtitle={t('subtitle')}>
      <div className="space-y-6">
        <div className="flex justify-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full border border-neon-cyan/30 bg-neon-cyan/10">
            <MailCheck className="h-8 w-8 text-neon-cyan" aria-hidden="true" />
          </div>
        </div>

        <p className="text-center text-sm font-mono text-muted-foreground">
          {t('sentToLabel')}{' '}
          <span className="text-neon-cyan">{email}</span>
        </p>

        <div aria-live="assertive" aria-atomic="true">
          {(localError || error) ? (
            <motion.div
              ref={errorRef}
              role="alert"
              tabIndex={-1}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm font-mono text-red-400 focus:outline-none focus:ring-2 focus:ring-red-500/50"
            >
              <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{localError || error}</span>
            </motion.div>
          ) : null}
        </div>

        <div className="space-y-3">
          <label className="block text-sm font-mono text-muted-foreground">
            {t('codeLabel')}
          </label>
          <CyberOtpInput value={code} onChange={setCode} maxLength={6} error={Boolean(localError || error)} />
          {attemptsRemaining !== null ? (
            <p className="text-center text-xs font-mono text-yellow-400">
              {t('attemptsRemaining', { count: attemptsRemaining })}
            </p>
          ) : null}
        </div>

        <motion.div
          whileHover={{ scale: isLoading ? 1 : 1.01 }}
          whileTap={{ scale: isLoading ? 1 : 0.99 }}
          className="flex justify-center"
        >
          <Button
            type="button"
            onClick={handleVerify}
            disabled={isLoading || code.length !== 6}
            className="min-w-[220px] h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label={isLoading ? t('submitting') : t('submitButton')}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                {t('submitting')}
              </>
            ) : (
              t('submitButton')
            )}
          </Button>
        </motion.div>

        <div className="space-y-3 text-center">
          <button
            type="button"
            onClick={handleResend}
            disabled={resendCountdown > 0 || isResending}
            className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4 disabled:cursor-not-allowed disabled:text-muted-foreground"
            aria-label={isResending ? t('resending') : t('resendButton')}
          >
            {isResending ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
                {t('resending')}
              </>
            ) : (
              <>
                <RefreshCw className="h-3 w-3" aria-hidden="true" />
                {resendCountdown > 0 ? t('resendCountdown', { seconds: resendCountdown }) : t('resendButton')}
              </>
            )}
          </button>
          {resendsRemaining !== null ? (
            <p className="text-xs font-mono text-muted-foreground">
              {t('resendsRemaining', { count: resendsRemaining })}
            </p>
          ) : null}
          <p className="text-sm font-mono text-muted-foreground">
            <Link
              href="/register"
              className="inline-flex items-center text-neon-purple hover:text-neon-purple/80 transition-colors underline underline-offset-4"
            >
              {t('backToRegister')}
            </Link>
          </p>
        </div>
      </div>
    </AuthFormCard>
  );
}
