'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { AlertCircle, Check, Loader2, UserPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link, useRouter } from '@/i18n/navigation';
import {
  AuthFormCard,
  CyberInput,
  RateLimitCountdown,
  useIsRateLimited,
} from '@/features/auth/components';
import { useAuthStore } from '@/stores/auth-store';

export default function RegisterClient() {
  const t = useTranslations('Auth.register');
  const router = useRouter();
  const { register, isLoading, error, clearError } = useAuthStore();
  const isRateLimited = useIsRateLimited();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [marketingConsent, setMarketingConsent] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);

  const passwordsMatch = password === confirmPassword && confirmPassword.length > 0;
  const canSubmit = Boolean(
    email && password && confirmPassword && acceptTerms && passwordsMatch && !isRateLimited,
  );

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
    if (!canSubmit) {
      return;
    }

    try {
      await register(email, password, {
        mode: 'email',
        tos_accepted: acceptTerms,
        marketing_consent: marketingConsent,
      });
      router.push(`/verify?email=${encodeURIComponent(email)}`);
    } catch {
      // Store state already reflects the error.
    }
  };

  return (
    <AuthFormCard title={t('title')} subtitle={t('subtitle')} className="keyboard-safe-bottom">
      <RateLimitCountdown />

      <div aria-live="assertive" aria-atomic="true">
        {error && !isRateLimited && (
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
        )}
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
          className="mobile-form-input"
        />

        <CyberInput
          label={t('passwordLabel')}
          type="password"
          prefix="pass"
          placeholder={t('passwordPlaceholder')}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
          autoComplete="new-password"
          disabled={isLoading || isRateLimited}
          className="mobile-form-input"
        />

        <CyberInput
          label={t('confirmPasswordLabel')}
          type="password"
          prefix="confirm"
          placeholder={t('confirmPasswordPlaceholder')}
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          required
          autoComplete="new-password"
          disabled={isLoading || isRateLimited}
          error={confirmPassword && !passwordsMatch ? t('passwordMismatch') : undefined}
          success={passwordsMatch}
          className="mobile-form-input"
        />

        <label className="touch-target flex items-start gap-3 cursor-pointer group">
          <div className="relative mt-0.5">
            <input
              type="checkbox"
              checked={acceptTerms}
              onChange={(event) => setAcceptTerms(event.target.checked)}
              className="peer sr-only"
              required
              aria-label={t('acceptTerms')}
            />
            <div className="flex h-5 w-5 items-center justify-center rounded border border-grid-line bg-terminal-bg transition-all peer-checked:border-neon-cyan peer-checked:bg-neon-cyan peer-focus:ring-2 peer-focus:ring-neon-cyan/50">
              {acceptTerms ? <Check className="h-3 w-3 text-black" /> : null}
            </div>
          </div>
          <span className="text-xs text-muted-foreground font-mono leading-relaxed group-hover:text-foreground transition-colors">
            {t('acceptTerms')}{' '}
            <Link href="/terms" className="touch-target inline-flex items-center text-neon-cyan hover:underline">
              {t('termsLink')}
            </Link>{' '}
            {t('and')}{' '}
            <Link href="/privacy-policy" className="touch-target inline-flex items-center text-neon-cyan hover:underline">
              {t('privacyLink')}
            </Link>
          </span>
        </label>

        <label className="touch-target flex items-start gap-3 cursor-pointer group">
          <div className="relative mt-0.5">
            <input
              type="checkbox"
              checked={marketingConsent}
              onChange={(event) => setMarketingConsent(event.target.checked)}
              className="peer sr-only"
              aria-label={t('marketingConsentLabel')}
            />
            <div className="flex h-5 w-5 items-center justify-center rounded border border-grid-line bg-terminal-bg transition-all peer-checked:border-neon-cyan peer-checked:bg-neon-cyan peer-focus:ring-2 peer-focus:ring-neon-cyan/50">
              {marketingConsent ? <Check className="h-3 w-3 text-black" /> : null}
            </div>
          </div>
          <span className="text-xs text-muted-foreground font-mono leading-relaxed group-hover:text-foreground transition-colors">
            {t('marketingConsentLabel')}
          </span>
        </label>

        <motion.div
          whileHover={{ scale: canSubmit ? 1.01 : 1 }}
          whileTap={{ scale: canSubmit ? 0.99 : 1 }}
          className="flex justify-center"
        >
          <Button
            type="submit"
            disabled={isLoading || !canSubmit}
            touchTarget="comfortable"
            className="min-w-[200px] h-12 bg-neon-purple hover:bg-neon-purple/90 text-white font-bold font-mono tracking-wider shadow-lg shadow-neon-purple/20 hover:shadow-neon-purple/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            aria-label={isLoading ? t('submitting') : t('submitButton')}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                {t('submitting')}
              </>
            ) : (
              <>
                <UserPlus className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('submitButton')}
              </>
            )}
          </Button>
        </motion.div>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground font-mono">
        {t('hasAccount')}{' '}
        <Link
          href="/login"
          className="touch-target inline-flex items-center text-neon-cyan hover:text-neon-cyan/80 transition-colors underline underline-offset-4"
        >
          {t('signInLink')}
        </Link>
      </p>
    </AuthFormCard>
  );
}
