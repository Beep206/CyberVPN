'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import type { AxiosError } from 'axios';
import { partnerAttributionApi } from '@/lib/api/partner-attribution';
import { useAuthStore } from '@/stores/auth-store';
import {
  clearPartnerAttribution,
  PARTNER_ATTRIBUTION_CHANGED_EVENT,
  readPartnerAttribution,
  savePartnerAttribution,
} from './storage';

const RETRY_DELAYS_MS = [1_000, 3_000, 10_000] as const;
const TERMINAL_CODES = new Set([
  'PARTNER_TRANSFER_NOT_FOUND',
  'PARTNER_TRANSFER_EXPIRED',
  'PARTNER_CODE_NOT_ACTIVE',
  'PARTNER_CODE_EXPIRED',
  'PARTNER_SELF_ATTRIBUTION_BLOCKED',
  'PARTNER_OWNER_NOT_CONFIGURED',
]);

function getApiErrorCode(error: unknown): string | null {
  const detail = (error as AxiosError<{ detail?: { code?: unknown } }>).response?.data?.detail;
  return typeof detail?.code === 'string' ? detail.code : null;
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

  useEffect(() => {
    const listener = () => setStorageVersion((value) => value + 1);
    window.addEventListener(PARTNER_ATTRIBUTION_CHANGED_EVENT, listener);
    return () => window.removeEventListener(PARTNER_ATTRIBUTION_CHANGED_EVENT, listener);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const locationKey = `${window.location.pathname}?${window.location.search}`;
    if (consumedLocationRef.current === locationKey) return;
    consumedLocationRef.current = locationKey;

    const url = new URL(window.location.href);
    const transferToken = url.searchParams.get('pat')?.trim();
    if (!transferToken) return;

    void withPartnerAttributionRetry(() =>
      partnerAttributionApi.consumeTransfer({ transfer_token: transferToken }),
    ).then((response) => {
      savePartnerAttribution({
        attributionId: response.data.attribution_id,
        capturedAt: new Date().toISOString(),
        expiresAt: response.data.expires_at,
        maskedCode: response.data.masked_code,
        sourceHost: window.location.host,
        sourcePath: pathname || window.location.pathname,
        version: 1,
      });
      removePartnerTransferQueryParam();
    }).catch((error) => {
      if (TERMINAL_CODES.has(getApiErrorCode(error) ?? '')) {
        clearPartnerAttribution();
        removePartnerTransferQueryParam();
      }
    });
  }, [pathname]);

  useEffect(() => {
    if (!isAuthenticated || !userId) return;
    const snapshot = readPartnerAttribution();
    const claimKey = snapshot
      ? `${userId}:${snapshot.attributionId}:${snapshot.capturedAt}`
      : `${userId}:partner-cookie-only`;
    if (claimAttemptRef.current === claimKey) return;
    claimAttemptRef.current = claimKey;

    void withPartnerAttributionRetry(() => partnerAttributionApi.claim()).then((response) => {
      if (
        response.data.status === 'claimed' ||
        response.data.status === 'already_claimed' ||
        response.data.status === 'expired' ||
        (response.data.status === 'no_pending' && snapshot)
      ) {
        clearPartnerAttribution();
      }
    }).catch((error) => {
      if (TERMINAL_CODES.has(getApiErrorCode(error) ?? '')) {
        clearPartnerAttribution();
      }
    });
  }, [isAuthenticated, storageVersion, userId]);

  return null;
}
