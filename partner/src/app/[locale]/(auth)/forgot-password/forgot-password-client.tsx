'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { AlertCircle, CheckCircle, KeyRound, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';
import {
  AuthFormCard,
  CyberInput,
  RateLimitCountdown,
  useIsRateLimited,
} from '@/features/auth/components';
import { authApi } from '@/lib/api/auth';
import { RateLimitError } from '@/lib/api/client';
import { useAuthStore } from '@/stores/auth-store';

export function ForgotPasswordClient() {
  const t = useTranslations('Auth.forgotPassword');
  const { clearError } = useAuthStore();
  const isRateLimited = useIsRateLimited();

  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    clearError();
  }, [clearError]);

  useEffect(() => {
    if (error && !isRateLimited && errorRef.current) {
      errorRef.current.focus();
    }
  }, [error, isRateLimited]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await authApi.forgotPassword({ email });
      setSent(true);
    } catch (err: unknown) {
      if (err instanceof RateLimitError) {
        setError(err.message);
      } else {
        setSent(true);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthFormCard title={t('title')} subtitle={t('subtitle')} className="keyboard-safe-bottom">
      <RateLimitCountdown />

      <div aria-live="assertive" aria-atomic="true">
        {error && !isRateLimited ? (
          <motion.div
            ref={errorRef}
            role="alert"
            tabIndex={-1}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm font-mono text-red-400 focus:outline-none focus:ring-2 focus:ring-red-500/50"
          >
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </motion.div>
        ) : null}
      </div>

      {sent ? (
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
            <p className="text-sm font-mono text-muted-foreground">
              {t('successMessage')}{' '}
              <span className="text-neon-cyan">{email}</span>
            </p>
            <p className="text-xs font-mono text-muted-foreground">{t('successExpiry')}</p>
          </div>

          <Link href={`/reset-password?email=${encodeURIComponent(email)}`}>
            <Button
              touchTarget="comfortable"
              className="min-w-[200px] h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all cursor-pointer"
              aria-label={t('continueToReset')}
            >
              <KeyRound className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('continueToReset')}
            </Button>
          </Link>

          <Button
            type="button"
            onClick={() => {
              setSent(false);
              setError(null);
            }}
            variant="outline"
            touchTarget="minimum"
            className="font-mono text-sm cursor-pointer border-grid-line/30 hover:border-neon-cyan/50"
            aria-label={t('sendAgain')}
          >
            {t('sendAgain')}
          </Button>
        </motion.div>
      ) : (
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
            className="mobile-form-input"
          />

          <motion.div
            whileHover={{ scale: isLoading || isRateLimited ? 1 : 1.01 }}
            whileTap={{ scale: isLoading || isRateLimited ? 1 : 0.99 }}
            className="flex justify-center"
          >
            <Button
              type="submit"
              disabled={isLoading || isRateLimited || !email}
              touchTarget="comfortable"
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
                  <KeyRound className="mr-2 h-4 w-4" aria-hidden="true" />
                  {t('submitButton')}
                </>
              )}
            </Button>
          </motion.div>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-muted-foreground font-mono">
        <Link
          href="/login"
          className="touch-target inline-flex items-center text-neon-cyan hover:text-neon-cyan/80 transition-colors underline underline-offset-4"
        >
          {t('backToLogin')}
        </Link>
      </p>
    </AuthFormCard>
  );
}
