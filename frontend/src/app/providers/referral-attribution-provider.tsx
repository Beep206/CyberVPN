'use client';

import { usePathname, useSearchParams } from 'next/navigation';
import { useEffect, useRef } from 'react';
import {
  extractReferralCode,
  normalizeReferralCode,
} from '@/features/referral-attribution/constants';
import {
  clearReferralAttribution,
  persistReferralAttribution,
  readReferralAttribution,
  replaceReferralAttribution,
} from '@/features/referral-attribution/storage';
import { referralApi } from '@/lib/api/referral';
import { useAuthStore } from '@/stores/auth-store';

const PERMANENT_CLAIM_FAILURES = new Set([400, 404, 409, 422]);

function getHttpStatus(error: unknown): number | null {
  if (typeof error !== 'object' || error === null) {
    return null;
  }

  const response = (error as { response?: unknown }).response;
  if (typeof response !== 'object' || response === null) {
    return null;
  }

  const status = (response as { status?: unknown }).status;
  return typeof status === 'number' ? status : null;
}

async function syncAttributionCookie(referralCode: string): Promise<string> {
  const response = await fetch('/api/referral-attribution', {
    body: JSON.stringify({ referral_code: referralCode }),
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Referral cookie sync failed with HTTP ${response.status}`);
  }

  const payload = await response.json() as { referral_code?: unknown };
  return normalizeReferralCode(
    typeof payload.referral_code === 'string' ? payload.referral_code : null,
  ) ?? referralCode;
}

async function clearAttributionCookie(): Promise<void> {
  const response = await fetch('/api/referral-attribution', {
    credentials: 'same-origin',
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Referral cookie cleanup failed with HTTP ${response.status}`);
  }
}

export function ReferralAttributionProvider() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const userId = useAuthStore((state) => state.user?.id ?? null);
  const claimAttemptRef = useRef<string | null>(null);
  const queryString = searchParams.toString();

  useEffect(() => {
    const referralCode = extractReferralCode(
      pathname,
      new URLSearchParams(queryString),
    );
    if (!referralCode) {
      return;
    }

    const attribution = persistReferralAttribution({
      code: referralCode,
      landingPath: pathname,
    });
    if (!attribution) {
      return;
    }

    void syncAttributionCookie(attribution.code)
      .then((effectiveCode) => {
        if (effectiveCode !== attribution.code) {
          replaceReferralAttribution({
            code: effectiveCode,
            landingPath: attribution.landingPath,
          });
        }
      })
      .catch((error: unknown) => {
        console.warn('[referral-attribution] cookie persistence failed', error);
      });
  }, [pathname, queryString]);

  useEffect(() => {
    if (!isAuthenticated || !userId) {
      claimAttemptRef.current = null;
      return;
    }

    const storedAttribution = readReferralAttribution();
    const referralCodeFromUrl = extractReferralCode(
      pathname,
      new URLSearchParams(queryString),
    );
    const referralCode = storedAttribution?.code ?? referralCodeFromUrl;
    const attemptKey = `${userId}:${referralCode ?? 'cookie-only'}`;

    if (claimAttemptRef.current === attemptKey) {
      return;
    }
    claimAttemptRef.current = attemptKey;

    void referralApi.claimAttribution(referralCode)
      .then(async () => {
        clearReferralAttribution();
        try {
          await clearAttributionCookie();
        } catch (error) {
          console.warn('[referral-attribution] cookie cleanup failed', error);
        }
      })
      .catch(async (error: unknown) => {
        const status = getHttpStatus(error);
        if (status !== null && PERMANENT_CLAIM_FAILURES.has(status)) {
          clearReferralAttribution();
          try {
            await clearAttributionCookie();
          } catch (cleanupError) {
            console.warn(
              '[referral-attribution] cookie cleanup after rejection failed',
              cleanupError,
            );
          }
          return;
        }

        // Keep the first-touch value for a later retry after transient auth,
        // network, feature-flag, or server failures.
        claimAttemptRef.current = null;
        console.warn('[referral-attribution] claim deferred', error);
      });
  }, [isAuthenticated, pathname, queryString, userId]);

  return null;
}
