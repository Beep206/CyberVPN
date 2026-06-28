'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import type { AxiosError } from 'axios';
import { partnerAttributionApi } from '@/lib/api/partner-attribution';
import { useAuthStore } from '@/stores/auth-store';
import {
  clearPartnerAttribution,
  PARTNER_ATTRIBUTION_CHANGED_EVENT,
  PARTNER_ATTRIBUTION_STORAGE_KEY,
  readPartnerAttribution,
  savePartnerAttribution,
} from './storage';

const RETRY_DELAYS_MS = [1_000, 3_000, 10_000, 30_000] as const;
const CLAIM_SUPPRESSION_PREFIX = 'cybervpn.partner_attribution.claim_suppressed.v1';
const DEFAULT_CLAIM_SUPPRESSION_MS = 10 * 60 * 1_000;
const TRANSIENT_CLAIM_SUPPRESSION_MS = 30_000;
const TERMINAL_CODES = new Set([
  'PARTNER_TRANSFER_TOKEN_INVALID',
  'PARTNER_TRANSFER_TOKEN_EXPIRED',
  'PARTNER_TRANSFER_TOKEN_CONSUMED',
  'PARTNER_ATTRIBUTION_SESSION_EXPIRED',
  'PARTNER_CODE_NOT_ACTIVE',
  'PARTNER_CODE_EXPIRED',
  'PARTNER_SELF_ATTRIBUTION_BLOCKED',
  'PARTNER_OWNER_NOT_CONFIGURED',
  'PARTNER_OWNER_TYPE_INVALID',
]);

function canUseSessionStorage(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return typeof window.sessionStorage !== 'undefined';
  } catch {
    return false;
  }
}

function getClaimSuppressionKey(claimKey: string): string {
  return `${CLAIM_SUPPRESSION_PREFIX}:${claimKey}`;
}

function isClaimSuppressed(claimKey: string): boolean {
  if (!canUseSessionStorage()) return false;
  const storageKey = getClaimSuppressionKey(claimKey);
  try {
    const raw = window.sessionStorage.getItem(storageKey);
    if (!raw) return false;
    const expiresAt = Number.parseInt(raw, 10);
    if (!Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
      window.sessionStorage.removeItem(storageKey);
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

function suppressClaim(claimKey: string, ttlMs = DEFAULT_CLAIM_SUPPRESSION_MS): void {
  if (!canUseSessionStorage()) return;
  try {
    window.sessionStorage.setItem(getClaimSuppressionKey(claimKey), String(Date.now() + ttlMs));
  } catch {
    // Session storage can be blocked; in-memory in-flight guards still prevent local duplicate bursts.
  }
}

function getApiErrorCode(error: unknown): string | null {
  const detail = (error as AxiosError<{ detail?: { code?: unknown } }>).response?.data?.detail;
  return typeof detail?.code === 'string' ? detail.code : null;
}

function getRetryAfterMs(error: unknown): number | null {
  const retryAfter = (error as AxiosError).response?.headers?.['retry-after'];
  const value = Array.isArray(retryAfter) ? retryAfter[0] : retryAfter;
  const seconds = Number.parseInt(String(value ?? ''), 10);
  if (!Number.isFinite(seconds) || seconds <= 0) return null;
  return seconds * 1_000;
}

function shouldRetry(error: unknown): boolean {
  const axiosError = error as AxiosError;
  const status = axiosError.response?.status;
  const code = getApiErrorCode(error);
  return code === 'PARTNER_ATTRIBUTION_TRANSIENT_FAILURE' || !status || status >= 500;
}

async function withPartnerAttributionRetry<T>(operation: () => Promise<T>): Promise<T> {
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

function removePartnerTransferQueryParam(): void {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  if (!url.searchParams.has('pat')) return;
  url.searchParams.delete('pat');
  window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`);
}

export function PartnerAttributionProvider() {
  const pathname = usePathname();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const userId = useAuthStore((state) => state.user?.id ?? null);
  const [storageVersion, setStorageVersion] = useState(0);
  const consumedLocationRef = useRef<string | null>(null);
  const claimAttemptRef = useRef<string | null>(null);
  const transferInFlightRef = useRef<string | null>(null);
  const claimInFlightRef = useRef<string | null>(null);

  useEffect(() => {
    const listener = () => setStorageVersion((value) => value + 1);
    const storageListener = (event: StorageEvent) => {
      if (event.key === PARTNER_ATTRIBUTION_STORAGE_KEY) {
        setStorageVersion((value) => value + 1);
      }
    };
    const resumeListener = () => setStorageVersion((value) => value + 1);
    window.addEventListener(PARTNER_ATTRIBUTION_CHANGED_EVENT, listener);
    window.addEventListener('storage', storageListener);
    window.addEventListener('online', resumeListener);
    window.addEventListener('visibilitychange', resumeListener);
    return () => {
      window.removeEventListener(PARTNER_ATTRIBUTION_CHANGED_EVENT, listener);
      window.removeEventListener('storage', storageListener);
      window.removeEventListener('online', resumeListener);
      window.removeEventListener('visibilitychange', resumeListener);
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const locationKey = `${window.location.pathname}?${window.location.search}`;
    if (consumedLocationRef.current === locationKey) return;
    if (transferInFlightRef.current === locationKey) return;

    const url = new URL(window.location.href);
    const transferToken = url.searchParams.get('pat')?.trim();
    if (!transferToken) return;
    transferInFlightRef.current = locationKey;

    void withPartnerAttributionRetry(() =>
      partnerAttributionApi.consumeTransfer({ transfer_token: transferToken }),
    ).then((response) => {
      consumedLocationRef.current = locationKey;
      savePartnerAttribution({
        attributionId: response.data.attribution_id,
        capturedAt: response.data.captured_at,
        expiresAt: response.data.expires_at,
        maskedCode: response.data.masked_code,
        sourceHost: window.location.host,
        sourcePath: pathname || window.location.pathname,
        version: 1,
      });
      removePartnerTransferQueryParam();
    }).catch((error) => {
      if (TERMINAL_CODES.has(getApiErrorCode(error) ?? '')) {
        consumedLocationRef.current = locationKey;
        clearPartnerAttribution();
        removePartnerTransferQueryParam();
      }
    }).finally(() => {
      transferInFlightRef.current = null;
    });
  }, [pathname, storageVersion]);

  useEffect(() => {
    if (!isAuthenticated || !userId) return;
    const snapshot = readPartnerAttribution();
    const claimKey = snapshot
      ? `${userId}:${snapshot.attributionId}:${snapshot.capturedAt}`
      : `${userId}:partner-cookie-only`;
    if (claimAttemptRef.current === claimKey) return;
    if (claimInFlightRef.current === claimKey) return;
    if (isClaimSuppressed(claimKey)) return;
    claimInFlightRef.current = claimKey;

    void withPartnerAttributionRetry(() => partnerAttributionApi.claim()).then((response) => {
      claimAttemptRef.current = claimKey;
      suppressClaim(claimKey);
      if (
        response.data.status === 'claimed' ||
        response.data.status === 'already_claimed' ||
        response.data.status === 'already_claimed_same_owner' ||
        response.data.status === 'rejected_existing_owner' ||
        response.data.status === 'expired' ||
        (response.data.status === 'no_pending' && snapshot)
      ) {
        clearPartnerAttribution();
      }
    }).catch((error) => {
      const code = getApiErrorCode(error);
      const retryAfterMs = getRetryAfterMs(error);
      const suppressionMs =
        retryAfterMs ?? (shouldRetry(error) ? TRANSIENT_CLAIM_SUPPRESSION_MS : DEFAULT_CLAIM_SUPPRESSION_MS);
      claimAttemptRef.current = claimKey;
      suppressClaim(claimKey, suppressionMs);
      if (TERMINAL_CODES.has(code ?? '')) {
        claimAttemptRef.current = claimKey;
        clearPartnerAttribution();
      }
    }).finally(() => {
      claimInFlightRef.current = null;
    });
  }, [isAuthenticated, storageVersion, userId]);

  return null;
}
