'use client';

import { startTransition, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useRouter } from '@/i18n/navigation';
import { motion } from 'motion/react';
import { AlertCircle, Copy, Loader2, RotateCcw, Send, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authAnalytics } from '@/lib/analytics';
import { authApi, type OAuthLoginResponse } from '@/lib/api/auth';
import {
  clearTelegramMagicLinkSession,
  readTelegramMagicLinkSession,
  type TelegramMagicLinkSession,
} from '@/features/auth/lib/telegram-magic-link-session';
import { useAuthStore } from '@/stores/auth-store';

const MAGIC_LINK_TTL_MS = 5 * 60 * 1000;
const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 150;

function applyTelegramLoginResult(result: OAuthLoginResponse): void {
  useAuthStore.setState({
    user: {
      id: result.user.id,
      email: result.user.email || '',
      login: result.user.login,
      is_active: result.user.is_active,
      is_email_verified: result.user.is_email_verified,
      role: 'viewer',
      created_at: result.user.created_at,
    },
    isAuthenticated: true,
    isLoading: false,
    isNewTelegramUser: result.is_new_user,
    error: null,
  });

  authAnalytics.telegramSuccess(result.user.id);
}

function openTelegram(session: TelegramMagicLinkSession, allowRedirectFallback: boolean): void {
  const telegramTarget = session.deepLinkUrl ?? session.botUrl;
  const popup = window.open(telegramTarget, '_blank', 'noopener,noreferrer');

  if (!popup && allowRedirectFallback) {
    window.location.href = telegramTarget;

    if (session.deepLinkUrl && session.botUrl !== session.deepLinkUrl) {
      window.setTimeout(() => {
        window.location.href = session.botUrl;
      }, 1200);
    }
  }
}

export default function TelegramLinkPage() {
  const searchParams = useSearchParams();
  const legacyBotToken = searchParams.get('token');
  const magicToken = searchParams.get('magic');
  const router = useRouter();
  const t = useTranslations('Auth.telegram');
  const retryT = useTranslations('Auth.oauthCallback');
  const loginWithBotLink = useAuthStore((state) => state.loginWithBotLink);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [magicLinkSession, setMagicLinkSession] = useState<TelegramMagicLinkSession | null>(() =>
    readTelegramMagicLinkSession()
  );
  const processedRouteTokenRef = useRef<string | null>(null);
  const activePollingTokenRef = useRef<string | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);
  const pollInFlightRef = useRef(false);
  const resumePollingRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const syncSessionFromStorage = () => {
      const storedSession = readTelegramMagicLinkSession();
      setMagicLinkSession((currentSession) => {
        const currentToken = currentSession?.token ?? null;
        const storedToken = storedSession?.token ?? null;
        return currentToken === storedToken ? currentSession : storedSession;
      });
    };

    syncSessionFromStorage();
    window.addEventListener('pageshow', syncSessionFromStorage);

    return () => {
      window.removeEventListener('pageshow', syncSessionFromStorage);
    };
  }, []);

  useEffect(() => {
    if (!legacyBotToken || processedRouteTokenRef.current === legacyBotToken) {
      return;
    }

    processedRouteTokenRef.current = legacyBotToken;
    window.history.replaceState({}, document.title, window.location.pathname);

    const handleBotLinkAuth = async () => {
      try {
        await loginWithBotLink(legacyBotToken);
        router.push('/dashboard');
      } catch (err: unknown) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        const detail = axiosError?.response?.data?.detail;
        if (detail?.toLowerCase().includes('expired')) {
          setError(t('botLinkExpired'));
        } else {
          setError(detail || t('botLinkInvalid'));
        }
      }
    };

    void handleBotLinkAuth();
  }, [legacyBotToken, loginWithBotLink, router, t]);

  useEffect(() => {
    if (legacyBotToken) {
      return;
    }

    const session = magicLinkSession ?? readTelegramMagicLinkSession();
    const currentMagicToken = magicToken ?? session?.token ?? null;

    if (!currentMagicToken) {
      activePollingTokenRef.current = null;
      resumePollingRef.current = null;
      startTransition(() => {
        setError(t('botLinkInvalid'));
      });
      return;
    }

    if (session && Date.now() - session.requestedAt > MAGIC_LINK_TTL_MS) {
      clearTelegramMagicLinkSession();
      activePollingTokenRef.current = null;
      resumePollingRef.current = null;
      setMagicLinkSession(null);
      startTransition(() => {
        setError(t('botLinkExpired'));
      });
      return;
    }

    if (activePollingTokenRef.current === currentMagicToken && resumePollingRef.current) {
      return;
    }

    activePollingTokenRef.current = currentMagicToken;
    attemptRef.current = 0;
    setError(null);

    let cancelled = false;

    const scheduleNextPoll = (attempt: number) => {
      attemptRef.current = attempt;
      pollTimeoutRef.current = setTimeout(() => {
        void pollMagicLinkStatus(attempt);
      }, POLL_INTERVAL_MS);
    };

    const pollMagicLinkStatus = async (attempt: number) => {
      if (cancelled || pollInFlightRef.current) return;
      pollInFlightRef.current = true;
      attemptRef.current = attempt;

      if (attempt >= MAX_POLL_ATTEMPTS) {
        clearTelegramMagicLinkSession();
        activePollingTokenRef.current = null;
        setMagicLinkSession(null);
        setError(t('botLinkExpired'));
        pollInFlightRef.current = false;
        return;
      }

      try {
        const { data } = await authApi.pollTelegramMagicLinkStatus(currentMagicToken);

        if (data.status === 'completed' && data.login_result) {
          clearTelegramMagicLinkSession();
          activePollingTokenRef.current = null;
          setMagicLinkSession(null);

          if (data.login_result.requires_2fa) {
            sessionStorage.setItem('tfa_token', data.login_result.tfa_token || '');
            router.push('/login?2fa=true');
            pollInFlightRef.current = false;
            return;
          }

          applyTelegramLoginResult(data.login_result);
          router.push(data.login_result.is_new_user ? '/dashboard?welcome=true' : '/dashboard');
          pollInFlightRef.current = false;
          return;
        }

        if (data.status === 'expired') {
          clearTelegramMagicLinkSession();
          activePollingTokenRef.current = null;
          setMagicLinkSession(null);
          setError(t('botLinkExpired'));
          pollInFlightRef.current = false;
          return;
        }
      } catch {
        if (attempt + 1 >= MAX_POLL_ATTEMPTS) {
          clearTelegramMagicLinkSession();
          activePollingTokenRef.current = null;
          setMagicLinkSession(null);
          setError(t('errors.authFailed'));
          pollInFlightRef.current = false;
          return;
        }
      } finally {
        if (!cancelled) {
          pollInFlightRef.current = false;
        }
      }

      scheduleNextPoll(attempt + 1);
    };

    const resumePolling = () => {
      if (cancelled) return;
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
      void pollMagicLinkStatus(attemptRef.current);
    };

    resumePollingRef.current = resumePolling;
    window.addEventListener('focus', resumePolling);
    window.addEventListener('pageshow', resumePolling);
    document.addEventListener('visibilitychange', resumePolling);

    void pollMagicLinkStatus(0);

    return () => {
      cancelled = true;
      resumePollingRef.current = null;
      window.removeEventListener('focus', resumePolling);
      window.removeEventListener('pageshow', resumePolling);
      document.removeEventListener('visibilitychange', resumePolling);
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, [legacyBotToken, magicLinkSession, magicToken, router, t]);

  const handleRetry = () => {
    clearTelegramMagicLinkSession();
    activePollingTokenRef.current = null;
    processedRouteTokenRef.current = null;
    setMagicLinkSession(null);
    setError(null);
    router.push('/login');
  };

  const handleOpenTelegram = () => {
    if (!magicLinkSession) return;
    openTelegram(magicLinkSession, true);
  };

  const handleCheckNow = () => {
    setMagicLinkSession(readTelegramMagicLinkSession());
    resumePollingRef.current?.();
  };

  const handleCopyStartCommand = async () => {
    if (!magicLinkSession) return;

    try {
      await navigator.clipboard.writeText(`/start auth_${magicLinkSession.token}`);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const startCommand = magicLinkSession ? `/start auth_${magicLinkSession.token}` : null;

  const renderStartCommandFallback = () => {
    if (!startCommand) return null;

    return (
      <div className="max-w-md rounded-lg border border-grid-line/30 bg-background/40 p-3 text-left">
        <p className="text-xs font-mono text-muted-foreground">{t('manualFallback')}</p>
        <div className="mt-2 flex items-center gap-2 rounded border border-grid-line/30 bg-background/60 px-3 py-2">
          <code className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-xs font-mono text-foreground">
            {startCommand}
          </code>
          <Button
            type="button"
            onClick={handleCopyStartCommand}
            variant="ghost"
            size="sm"
            className="h-8 px-2 font-mono text-xs"
            aria-label={t('copyStartCommand')}
          >
            <Copy className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            {copied ? t('copiedStartCommand') : t('copyStartCommand')}
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col items-center justify-center gap-6 text-center">
      {error ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center gap-4 rounded-xl border border-red-500/20 bg-terminal-surface/80 p-8 backdrop-blur-md"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-red-500/20 bg-red-500/10">
            <AlertCircle className="h-6 w-6 text-red-400" aria-hidden="true" />
          </div>
          <p className="max-w-sm text-sm font-mono text-muted-foreground" role="alert">
            {error}
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            {magicLinkSession ? (
              <Button
                onClick={handleOpenTelegram}
                className="bg-[#2AABEE] font-bold font-mono text-white hover:bg-[#2AABEE]/90"
                aria-label={t('loginButton')}
              >
                <Send className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('loginButton')}
              </Button>
            ) : null}
            <Button
              type="button"
              onClick={handleCheckNow}
              variant="outline"
              className="border-grid-line/40 font-bold font-mono"
              aria-label={t('checkStatusButton')}
            >
              <Shield className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('checkStatusButton')}
            </Button>
            <Button
              onClick={handleRetry}
              className="bg-neon-cyan font-bold font-mono text-black hover:bg-neon-cyan/90"
              aria-label={retryT('tryAgain')}
            >
              <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" />
              {retryT('tryAgain')}
            </Button>
          </div>
          {renderStartCommandFallback()}
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-4 rounded-xl border border-grid-line/30 bg-terminal-surface/80 p-8 backdrop-blur-md"
        >
          <div className="relative">
            <div className="flex h-16 w-16 items-center justify-center rounded-full border border-neon-cyan/20 bg-neon-cyan/10">
              <Shield className="h-8 w-8 text-neon-cyan" aria-hidden="true" />
            </div>
            <Loader2 className="absolute -right-1 -top-1 h-6 w-6 animate-spin text-neon-cyan" aria-hidden="true" />
          </div>
          <div className="space-y-1">
            <h2 className="font-display text-lg font-bold text-foreground">
              {t('botLinkAuth')}
            </h2>
            <p className="text-xs font-mono text-muted-foreground">{t('connecting')}</p>
          </div>
          {magicLinkSession ? (
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Button
                onClick={handleOpenTelegram}
                className="bg-[#2AABEE] font-bold font-mono text-white hover:bg-[#2AABEE]/90"
                aria-label={t('loginButton')}
              >
                <Send className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('loginButton')}
              </Button>
              <Button
                type="button"
                onClick={handleCheckNow}
                variant="outline"
                className="border-grid-line/40 font-bold font-mono"
                aria-label={t('checkStatusButton')}
              >
                <Shield className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('checkStatusButton')}
              </Button>
            </div>
          ) : null}
          {renderStartCommandFallback()}
        </motion.div>
      )}
    </div>
  );
}
