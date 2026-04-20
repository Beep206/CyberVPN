'use client';

import { useEffect, useRef, useState } from 'react';
import { useLocale } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { motion } from 'motion/react';
import { AlertCircle, Loader2, LogIn } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link, useRouter } from '@/i18n/navigation';
import {
  AuthFormCard,
  CyberInput,
  RateLimitCountdown,
  useIsRateLimited,
} from '@/features/auth/components';
import { stagePendingTwoFactorSession } from '@/features/auth/lib/pending-twofa-client';
import { getSafeRedirectPath } from '@/features/auth/lib/redirect-path';
import { authApi } from '@/lib/api/auth';
import { RateLimitError } from '@/lib/api/client';

type StorefrontLoginClientProps = {
  title: string;
  subtitle: string;
};

function buildTwoFactorLoginUrl(locale: string, redirectTarget: string): string {
  const params = new URLSearchParams({ '2fa': 'true' });
  if (redirectTarget) {
    params.set('redirect', redirectTarget);
  }

  return `/${locale}/login?${params.toString()}`;
}

function readErrorMessage(error: unknown, fallback: string): string {
  const axiosError = error as { response?: { data?: { detail?: unknown } } };
  const detail = axiosError.response?.data?.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map((item: { msg?: string }) => item.msg || JSON.stringify(item)).join(', ');
  }

  return fallback;
}

export function StorefrontLoginClient({
  title,
  subtitle,
}: StorefrontLoginClientProps) {
  const locale = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();
  const isRateLimited = useIsRateLimited();
  const isTwoFactorFlow = searchParams.get('2fa') === 'true';

  const redirectPath = searchParams.get('redirect')
    ? getSafeRedirectPath(searchParams.get('redirect'), locale)
    : `/${locale}`;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (error && !isRateLimited && errorRef.current) {
      errorRef.current.focus();
    }
  }, [error, isRateLimited]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const { data } = await authApi.login({ email, password });

      if (data.requires_2fa && data.tfa_token) {
        await stagePendingTwoFactorSession({
          token: data.tfa_token,
          locale,
          returnTo: redirectPath,
        });

        window.location.href = buildTwoFactorLoginUrl(locale, redirectPath);
        return;
      }

      await authApi.session();
      router.push(redirectPath);
    } catch (requestError) {
      if (requestError instanceof RateLimitError) {
        setError(requestError.message);
      } else {
        setError(readErrorMessage(requestError, 'Customer sign-in failed.'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleTwoFactorSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/2fa/complete', {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
        },
        body: JSON.stringify({ code: twoFactorCode }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({ detail: 'Two-factor verification failed.' }));
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Two-factor verification failed.');
      }

      const payload = await response.json() as { redirect_to: string };
      window.location.href = payload.redirect_to;
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Two-factor verification failed.');
      setIsLoading(false);
    }
  };

  return (
    <AuthFormCard title={title} subtitle={subtitle} className="keyboard-safe-bottom">
      <RateLimitCountdown />
      <div aria-live="assertive" aria-atomic="true">
        {error && !isRateLimited ? (
          <motion.div
            ref={errorRef}
            role="alert"
            tabIndex={-1}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm font-mono text-red-400 focus:outline-none focus:ring-2 focus:ring-red-500/50"
          >
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </motion.div>
        ) : null}
      </div>
      {isTwoFactorFlow ? (
        <form onSubmit={handleTwoFactorSubmit} className="space-y-5" aria-busy={isLoading}>
          <CyberInput
            label="2FA code"
            type="text"
            prefix="2fa"
            placeholder="123456"
            value={twoFactorCode}
            onChange={(event) => setTwoFactorCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
            required
            autoComplete="one-time-code"
            disabled={isLoading}
            className="mobile-form-input"
          />
          <Button
            type="submit"
            disabled={isLoading || twoFactorCode.length !== 6}
            touchTarget="comfortable"
            className="min-w-[200px] h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Verifying
              </>
            ) : (
              <>
                <LogIn className="mr-2 h-4 w-4" />
                Verify and continue
              </>
            )}
          </Button>
        </form>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5" aria-busy={isLoading}>
          <CyberInput
            label="Email"
            type="email"
            prefix="email"
            placeholder="customer@brand.example"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
            disabled={isLoading || isRateLimited}
            className="mobile-form-input"
          />
          <CyberInput
            label="Password"
            type="password"
            prefix="pass"
            placeholder="••••••••"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
            disabled={isLoading || isRateLimited}
            className="mobile-form-input"
          />
          <div className="flex items-center justify-between gap-3">
            <Link
              href="/"
              className="touch-target inline-flex items-center text-neon-purple hover:text-neon-purple/80 font-mono text-xs transition-colors"
            >
              Back to storefront
            </Link>
            <Link
              href="/forgot-password"
              className="touch-target inline-flex items-center text-neon-cyan hover:text-neon-cyan/80 font-mono text-xs transition-colors"
            >
              Forgot password
            </Link>
          </div>
          <Button
            type="submit"
            disabled={isLoading || isRateLimited}
            touchTarget="comfortable"
            className="min-w-[200px] h-12 bg-neon-cyan hover:bg-neon-cyan/90 text-black font-bold font-mono tracking-wider shadow-lg shadow-neon-cyan/20 hover:shadow-neon-cyan/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Signing in
              </>
            ) : (
              <>
                <LogIn className="mr-2 h-4 w-4" />
                Continue to checkout
              </>
            )}
          </Button>
        </form>
      )}
    </AuthFormCard>
  );
}
