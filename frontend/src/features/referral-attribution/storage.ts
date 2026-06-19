'use client';

export const REFERRAL_ATTRIBUTION_STORAGE_KEY = 'cybervpn.referral_attribution.v2';
export const REFERRAL_ATTRIBUTION_CHANGED_EVENT = 'cybervpn:referral-attribution-changed';

export type ReferralAttributionSnapshot = {
  attributionId: string | null;
  capturedAt: string;
  code: string;
  expiresAt: string;
  maskedCode: string;
  sourceHost: string | null;
  sourcePath: string | null;
  version: 2;
};

function canUseStorage(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const storage = window.localStorage;
    return typeof storage !== 'undefined';
  } catch {
    return false;
  }
}

function emitChanged(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(REFERRAL_ATTRIBUTION_CHANGED_EVENT));
}

function parseSnapshot(raw: string | null): ReferralAttributionSnapshot | null {
  if (!raw) return null;

  try {
    const value = JSON.parse(raw) as Partial<ReferralAttributionSnapshot>;
    if (
      value.version !== 2 ||
      typeof value.code !== 'string' ||
      typeof value.capturedAt !== 'string' ||
      typeof value.expiresAt !== 'string'
    ) {
      return null;
    }

    return {
      attributionId: typeof value.attributionId === 'string' ? value.attributionId : null,
      capturedAt: value.capturedAt,
      code: value.code,
      expiresAt: value.expiresAt,
      maskedCode: typeof value.maskedCode === 'string' ? value.maskedCode : maskReferralCode(value.code),
      sourceHost: typeof value.sourceHost === 'string' ? value.sourceHost : null,
      sourcePath: typeof value.sourcePath === 'string' ? value.sourcePath : null,
      version: 2,
    };
  } catch {
    return null;
  }
}

export function normalizeReferralCode(rawCode: string | null | undefined): string | null {
  const normalized = rawCode?.trim().toUpperCase();
  if (!normalized || !/^[A-Z0-9_-]{4,64}$/.test(normalized)) {
    return null;
  }
  return normalized;
}

export function maskReferralCode(code: string): string {
  const prefix = normalizeReferralCode(code)?.slice(0, 4) ?? '';
  return prefix ? `${prefix}****` : '****';
}

export function isReferralAttributionExpired(snapshot: ReferralAttributionSnapshot): boolean {
  const expiresAt = new Date(snapshot.expiresAt).getTime();
  return !Number.isFinite(expiresAt) || expiresAt <= Date.now();
}

export function readReferralAttribution(): ReferralAttributionSnapshot | null {
  if (!canUseStorage()) return null;

  let snapshot: ReferralAttributionSnapshot | null;
  try {
    snapshot = parseSnapshot(window.localStorage.getItem(REFERRAL_ATTRIBUTION_STORAGE_KEY));
  } catch {
    return null;
  }
  if (!snapshot) {
    try {
      window.localStorage.removeItem(REFERRAL_ATTRIBUTION_STORAGE_KEY);
    } catch {
      return null;
    }
    return null;
  }

  if (isReferralAttributionExpired(snapshot)) {
    clearReferralAttribution();
    return null;
  }

  return snapshot;
}

export function saveReferralAttribution(snapshot: ReferralAttributionSnapshot): void {
  if (!canUseStorage()) return;
  try {
    window.localStorage.setItem(REFERRAL_ATTRIBUTION_STORAGE_KEY, JSON.stringify(snapshot));
    emitChanged();
  } catch {
    // Browser storage can be blocked; the HttpOnly cookie remains the canonical source.
  }
}

export function clearReferralAttribution(): void {
  if (!canUseStorage()) return;
  try {
    window.localStorage.removeItem(REFERRAL_ATTRIBUTION_STORAGE_KEY);
    emitChanged();
  } catch {
    // Ignore blocked storage.
  }
}
