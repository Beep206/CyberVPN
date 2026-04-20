'use client';

import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { AlertCircle, CheckCircle, Loader2, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link, useRouter } from '@/i18n/navigation';
import {
  AuthFormCard,
  CyberInput,
  CyberOtpInput,
  RateLimitCountdown,
  useIsRateLimited,
} from '@/features/auth/components';
import { authApi } from '@/lib/api/auth';
import { RateLimitError } from '@/lib/api/client';
import { useAuthStore } from '@/stores/auth-store';

export function ResetPasswordClient() {
  const t = useTranslations('Auth.resetPassword');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { clearError } = useAuthStore();
  const isRateLimited = useIsRateLimited();

  const [email, setEmail] = useState(searchParams.get('email') ?? '');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    clearError();
  }, [clearError]);

  useEffect(() => {
    if ((error || validationError) && !isRateLimited && errorRef.current) {
      errorRef.current.focus();
    }
  }, [error, isRateLimited, validationError]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setValidationError(null);

    if (newPassword !== confirmPassword) {
      setValidationError(t('passwordMismatch'));
      return;
    }

    setIsLoading(true);
    try {
      await authApi.resetPassword({
        email,
        code,
        new_password: newPassword,
      });
      setSuccess(true);
    } catch (err: unknown) {
      if (err instanceof RateLimitError) {
        setError(err.message);
      } else {
        const axiosError = err as { response?: { data?: { detail?: string; code?: string } } };
        const errorCode = axiosError.response?.data?.code;
        const errorMessage = axiosError.response?.data?.detail;

        if (errorCode === 'expired' || errorMessage?.toLowerCase().includes('expired')) {
          setError(t('codeExpired'));
        } else {
          setError(errorMessage || t('invalidCode'));
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <AuthFormCard title={t('successTitle')} subtitle={t('successMessage')}>
        <motion.div
          aria-live="assertive"
          aria-atomic="true"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center gap-4 py-6"
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-full border border-matrix-green/20 bg-matrix-green/10">
            <CheckCircle className="h-8 w-8 text-matrix-green" aria-hidden="true" />
          </div>
          <div className="space-y-2 text-center">
            <h3 className="font-display text-lg font-bold text-foreground">{t('successTitle')}</h3>
            <p className="text-sm font-mono text-muted-foreground">{t('successMessage')}</p>
          </div>
          <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }} className="flex justify-center">
            <Button
              type="button"
              onClick={() => router.push('/login')}
              className="min-w-[200px] h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all cursor-pointer"
              aria-label={t('goToLogin')}
            >
              <ShieldCheck className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('goToLogin')}
            </Button>
          </motion.div>
        </motion.div>
      </AuthFormCard>
    );
  }

  return (
    <AuthFormCard title={t('title')} subtitle={t('subtitle')}>
      <RateLimitCountdown />

      <div aria-live="assertive" aria-atomic="true">
        {(error || validationError) ? (
          <motion.div
            ref={errorRef}
            role="alert"
            tabIndex={-1}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm font-mono text-red-400 focus:outline-none focus:ring-2 focus:ring-red-500/50"
          >
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error || validationError}</span>
          </motion.div>
        ) : null}
      </div>

      <form onSubmit={handleSubmit} className="space-y-5" aria-busy={isLoading}>
        <CyberInput
          label={t('emailLabel')}
          type="email"
          prefix="email"
          placeholder={t('emailPlaceholder')}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
          autoComplete="email"
          disabled={isLoading || isRateLimited}
        />

        <div className="space-y-2">
          <label className="block text-sm font-mono text-muted-foreground">{t('codeLabel')}</label>
          <CyberOtpInput value={code} onChange={setCode} maxLength={6} error={Boolean(error)} />
        </div>

        <CyberInput
          label={t('newPasswordLabel')}
          type="password"
          prefix="pass"
          placeholder={t('newPasswordPlaceholder')}
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          required
          autoComplete="new-password"
          disabled={isLoading || isRateLimited}
          error={validationError || undefined}
        />

        <CyberInput
          label={t('confirmPasswordLabel')}
          type="password"
          prefix="pass"
          placeholder={t('confirmPasswordPlaceholder')}
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          required
          autoComplete="new-password"
          disabled={isLoading || isRateLimited}
          error={validationError || undefined}
        />

        <motion.div
          whileHover={{ scale: isLoading || isRateLimited ? 1 : 1.01 }}
          whileTap={{ scale: isLoading || isRateLimited ? 1 : 0.99 }}
          className="flex justify-center"
        >
          <Button
            type="submit"
            disabled={isLoading || isRateLimited || !email || !code || !newPassword || !confirmPassword}
            className="min-w-[200px] h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label={isLoading ? t('submitting') : t('submitButton')}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                {t('submitting')}
              </>
            ) : (
              <>
                <ShieldCheck className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('submitButton')}
              </>
            )}
          </Button>
        </motion.div>
      </form>

      <div className="mt-6 flex flex-col items-center gap-2">
        <Link
          href="/forgot-password"
          className="text-sm text-muted-foreground hover:text-neon-purple font-mono transition-colors underline underline-offset-4"
        >
          {t('backToForgot')}
        </Link>
        <Link
          href="/login"
          className="text-sm text-neon-cyan hover:text-neon-cyan/80 font-mono transition-colors underline underline-offset-4"
        >
          {t('backToLogin')}
        </Link>
      </div>
    </AuthFormCard>
  );
}
