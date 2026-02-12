'use client';

import { useEffect, useState, useRef, startTransition } from 'react';
import { useRateLimitUntil, useAuthStore } from '@/stores/auth-store';
import { useTranslations } from 'next-intl';

export function RateLimitCountdown() {
  const rateLimitUntil = useRateLimitUntil();
  const clearRateLimit = useAuthStore((s) => s.clearRateLimit);
  const t = useTranslations('Auth.errors');
  const [secondsRemaining, setSecondsRemaining] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!rateLimitUntil) {
      startTransition(() => setSecondsRemaining(0));
      return;
    }

    const updateCountdown = () => {
      const remaining = Math.max(0, Math.ceil((rateLimitUntil - Date.now()) / 1000));
      setSecondsRemaining(remaining);

      if (remaining <= 0) {
        clearRateLimit();
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    };

    updateCountdown();
    intervalRef.current = setInterval(updateCountdown, 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [rateLimitUntil, clearRateLimit]);

  if (!rateLimitUntil || secondsRemaining <= 0) {
    return null;
  }

  const minutes = Math.floor(secondsRemaining / 60);
  const seconds = secondsRemaining % 60;
  const formattedTime = minutes > 0 
    ? String(minutes) + ':' + String(seconds).padStart(2, '0')
    : String(secondsRemaining);

  return (
    <div role="status" aria-live="polite" className="flex items-center justify-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-red-400">
      <svg
        className="h-5 w-5 animate-pulse"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <span className="font-mono text-sm">
        {minutes > 0
          ? t('rateLimitedMinutes', { minutes: formattedTime })
          : t('rateLimited', { seconds: secondsRemaining })}
      </span>
    </div>
  );
}

export function useIsRateLimited(): boolean {
  const rateLimitUntil = useRateLimitUntil();
  const [now] = useState(() => Date.now());
  return rateLimitUntil !== null && rateLimitUntil > now;
}
