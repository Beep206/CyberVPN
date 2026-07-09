'use client';

export const PARTNER_ATTRIBUTION_STORAGE_KEY = 'cybervpn.partner_attribution.v1';
export const PARTNER_ATTRIBUTION_CHANGED_EVENT = 'cybervpn:partner-attribution-changed';

export type PartnerAttributionSnapshot = {
  attributionId: string;
  capturedAt: string;
  expiresAt: string;
  maskedCode: string;
  sourceHost: string | null;
  sourcePath: string | null;
  version: 1;
};

function canUseStorage(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return typeof window.localStorage !== 'undefined';
  } catch {
    return false;
  }
}

function emitChanged(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(PARTNER_ATTRIBUTION_CHANGED_EVENT));
}

function parseSnapshot(raw: string | null): PartnerAttributionSnapshot | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as Partial<PartnerAttributionSnapshot>;
    if (
      value.version !== 1 ||
      typeof value.attributionId !== 'string' ||
      typeof value.expiresAt !== 'string' ||
      typeof value.maskedCode !== 'string'
    ) {
      return null;
    }
    return {
      attributionId: value.attributionId,
      capturedAt: typeof value.capturedAt === 'string' ? value.capturedAt : new Date().toISOString(),
      expiresAt: value.expiresAt,
      maskedCode: value.maskedCode,
      sourceHost: typeof value.sourceHost === 'string' ? value.sourceHost : null,
      sourcePath: typeof value.sourcePath === 'string' ? value.sourcePath : null,
      version: 1,
    };
  } catch {
    return null;
  }
}

export function isPartnerAttributionExpired(snapshot: PartnerAttributionSnapshot): boolean {
  const expiresAt = new Date(snapshot.expiresAt).getTime();
  return !Number.isFinite(expiresAt) || expiresAt <= Date.now();
}

export function readPartnerAttribution(): PartnerAttributionSnapshot | null {
  if (!canUseStorage()) return null;

  let raw: string | null;
  try {
    raw = window.localStorage.getItem(PARTNER_ATTRIBUTION_STORAGE_KEY);
  } catch {
    return null;
  }

  const snapshot = parseSnapshot(raw);
  if (!snapshot) {
    if (raw !== null) {
      try {
        window.localStorage.removeItem(PARTNER_ATTRIBUTION_STORAGE_KEY);
      } catch {
        // Ignore blocked storage.
      }
    }
    return null;
  }
  if (isPartnerAttributionExpired(snapshot)) {
    clearPartnerAttribution();
    return null;
  }
  return snapshot;
}

export function savePartnerAttribution(snapshot: PartnerAttributionSnapshot): void {
  if (!canUseStorage()) return;
  try {
    window.localStorage.setItem(PARTNER_ATTRIBUTION_STORAGE_KEY, JSON.stringify(snapshot));
    emitChanged();
  } catch {
    // Browser storage can be blocked; the HttpOnly cookie remains canonical.
  }
}

export function clearPartnerAttribution(): void {
  if (!canUseStorage()) return;
  try {
    const hadSnapshot = window.localStorage.getItem(PARTNER_ATTRIBUTION_STORAGE_KEY) !== null;
    window.localStorage.removeItem(PARTNER_ATTRIBUTION_STORAGE_KEY);
    if (hadSnapshot) {
      emitChanged();
    }
  } catch {
    // Ignore blocked storage.
  }
}
