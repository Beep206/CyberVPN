'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import type { AxiosError } from 'axios';
import { referralApi } from '@/lib/api/referral';
import { useAuthStore } from '@/stores/auth-store';
import {
  clearReferralAttribution,
  maskReferralCode,
  normalizeReferralCode,
  readReferralAttribution,
  REFERRAL_ATTRIBUTION_CHANGED_EVENT,
  saveReferralAttribution,
  type ReferralAttributionSnapshot,
} from './storage';

const RETRY_DELAYS_MS = [1_000, 3_000, 10_000] as const;
const REFERRAL_QUERY_KEYS = ['ref', 'referral', 'code'] as const;
const CAMPAIGN_KEYS = [
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_term',
  'utm_content',
  'gclid',
  'fbclid',
  'click_id',
  'sub_id',
] as const;

const TERMINAL_CLAIM_CODES = new Set([
  'REFERRAL_CODE_INVALID',
  'REFERRAL_CODE_NOT_FOUND',
  'REFERRAL_CODE_INACTIVE',
  'REFERRAL_SELF_ATTRIBUTION_BLOCKED',
  'REFERRAL_PARTNER_ATTRIBUTION_CONFLICT',
  'REFERRAL_ALREADY_CLAIMED',
  'REFERRAL_ATTRIBUTION_EXPIRED',
]);

function getApiErrorCode(error: unknown): string | null {
  const detail = (error as AxiosError<{ detail?: { code?: unknown } }>).response?.data?.detail;
  return typeof detail?.code === 'string' ? detail.code : null;
}

function shouldRetry(error: unknown): boolean {
  const axiosError = error as AxiosError;
  const status = axiosError.response?.status;
  const code = getApiErrorCode(error);
  return code === 'REFERRAL_TRANSIENT_FAILURE' || !status || status >= 500;
}

async function withReferralRetry<T>(operation: () => Promise<T>): Promise<T> {
  let lastError: unknown;

  for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      if (!shouldRetry(error) || attempt >= RETRY_DELAYS_MS.length) {
        throw error;
      }
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAYS_MS[attempt]));
    }
  }

  throw lastError;
}

function getReferralCodeFromSearch(searchParams: URLSearchParams): string | null {
  for (const key of REFERRAL_QUERY_KEYS) {
    const normalized = normalizeReferralCode(searchParams.get(key));
    if (normalized) return normalized;
  }
  return null;
}

function collectCampaignParams(searchParams: URLSearchParams): Record<string, string> {
  const params: Record<string, string> = {};
  for (const key of CAMPAIGN_KEYS) {
    const value = searchParams.get(key)?.trim();
    if (value) {
      params[key] = value.slice(0, 160);
    }
  }
  return params;
}

function removeReferralQueryParams(): void {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  let changed = false;
  for (const key of REFERRAL_QUERY_KEYS) {
    if (url.searchParams.has(key)) {
      url.searchParams.delete(key);
      changed = true;
    }
  }
  if (changed) {
    window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`);
  }
}

function createLocalSnapshot({
  attributionId,
  code,
  capturedAt,
  expiresAt,
  maskedCode,
}: {
  attributionId: string | null;
  capturedAt: string;
  code: string;
  expiresAt: string;
  maskedCode?: string | null;
}): ReferralAttributionSnapshot {
  return {
    attributionId,
    capturedAt,
    code,
    expiresAt,
    maskedCode: maskedCode || maskReferralCode(code),
    sourceHost: typeof window !== 'undefined' ? window.location.host : null,
    sourcePath: typeof window !== 'undefined' ? window.location.pathname : null,
    version: 2,
  };
}

export function ReferralAttributionProvider() {
  const pathname = usePathname();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const userId = useAuthStore((state) => state.user?.id ?? null);
  const [storageVersion, setStorageVersion] = useState(0);
  const capturedLocationRef = useRef<string | null>(null);
  const claimAttemptRef = useRef<string | null>(null);

  useEffect(() => {
    const listener = () => setStorageVersion((value) => value + 1);
    window.addEventListener(REFERRAL_ATTRIBUTION_CHANGED_EVENT, listener);
    return () => window.removeEventListener(REFERRAL_ATTRIBUTION_CHANGED_EVENT, listener);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const locationKey = `${window.location.pathname}?${window.location.search}`;
    if (capturedLocationRef.current === locationKey) {
      return;
    }
    capturedLocationRef.current = locationKey;

    const searchParams = new URLSearchParams(window.location.search);
    const referralCode = getReferralCodeFromSearch(searchParams);
    if (!referralCode) {
      return;
    }

    const existing = readReferralAttribution();
    if (existing) {
      removeReferralQueryParams();
      return;
    }

    void withReferralRetry(() =>
      referralApi.captureAttribution({
        referral_code: referralCode,
        source_host: window.location.host,
        source_path: pathname || window.location.pathname,
        campaign_params: collectCampaignParams(searchParams),
      }),
    ).then((response) => {
      saveReferralAttribution(createLocalSnapshot({
        attributionId: response.data.attribution_id,
        capturedAt: response.data.captured_at,
        code: referralCode,
        expiresAt: response.data.expires_at,
        maskedCode: response.data.masked_code,
      }));
      removeReferralQueryParams();
    }).catch((error) => {
      if (TERMINAL_CLAIM_CODES.has(getApiErrorCode(error) ?? '')) {
        clearReferralAttribution();
      }
    });
  }, [pathname]);

  useEffect(() => {
    if (!isAuthenticated || !userId) {
      return;
    }

    const snapshot = readReferralAttribution();
    const claimKey = snapshot
      ? `${userId}:${snapshot.code}:${snapshot.capturedAt}`
      : `${userId}:cookie-only`;
    if (claimAttemptRef.current === claimKey) {
      return;
    }
    claimAttemptRef.current = claimKey;

    void withReferralRetry(() =>
      referralApi.claimAttribution({
        fallback_referral_code: snapshot?.code,
      }),
    ).then((response) => {
      if (response.data.status === 'claimed' || response.data.status === 'already_claimed') {
        clearReferralAttribution();
      } else if (response.data.status === 'no_pending' && snapshot) {
        clearReferralAttribution();
      }
    }).catch((error) => {
      if (TERMINAL_CLAIM_CODES.has(getApiErrorCode(error) ?? '')) {
        clearReferralAttribution();
      }
    });
  }, [isAuthenticated, storageVersion, userId]);

  return null;
}
