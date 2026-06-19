import {
  normalizeReferralCode,
  REFERRAL_ATTRIBUTION_STORAGE_KEY,
  REFERRAL_ATTRIBUTION_TTL_MS,
} from './constants';

export type StoredReferralAttribution = {
  capturedAt: number;
  code: string;
  expiresAt: number;
  landingPath: string;
  version: 1;
};

type ReferralStorage = Pick<Storage, 'getItem' | 'removeItem' | 'setItem'>;

function getLocalStorage(): ReferralStorage | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    return window.localStorage;
  } catch (error) {
    console.warn('[referral-attribution] localStorage is unavailable', error);
    return null;
  }
}

function isStoredReferralAttribution(value: unknown): value is StoredReferralAttribution {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  const candidate = value as Partial<StoredReferralAttribution>;
  return (
    candidate.version === 1
    && typeof candidate.code === 'string'
    && normalizeReferralCode(candidate.code) === candidate.code
    && typeof candidate.capturedAt === 'number'
    && Number.isFinite(candidate.capturedAt)
    && typeof candidate.expiresAt === 'number'
    && Number.isFinite(candidate.expiresAt)
    && typeof candidate.landingPath === 'string'
  );
}

function removeStoredValue(storage: ReferralStorage): void {
  try {
    storage.removeItem(REFERRAL_ATTRIBUTION_STORAGE_KEY);
  } catch (error) {
    console.warn('[referral-attribution] failed to clear localStorage', error);
  }
}

export function readReferralAttribution(
  storage: ReferralStorage | null = getLocalStorage(),
  now = Date.now(),
): StoredReferralAttribution | null {
  if (!storage) {
    return null;
  }

  try {
    const rawValue = storage.getItem(REFERRAL_ATTRIBUTION_STORAGE_KEY);
    if (!rawValue) {
      return null;
    }

    const parsedValue: unknown = JSON.parse(rawValue);
    if (!isStoredReferralAttribution(parsedValue) || parsedValue.expiresAt <= now) {
      removeStoredValue(storage);
      return null;
    }

    return parsedValue;
  } catch (error) {
    console.warn('[referral-attribution] failed to read localStorage', error);
    removeStoredValue(storage);
    return null;
  }
}

function createAttribution(
  code: string,
  landingPath: string,
  now: number,
): StoredReferralAttribution {
  return {
    capturedAt: now,
    code,
    expiresAt: now + REFERRAL_ATTRIBUTION_TTL_MS,
    landingPath,
    version: 1,
  };
}

function writeAttribution(
  attribution: StoredReferralAttribution,
  storage: ReferralStorage | null,
): StoredReferralAttribution {
  if (!storage) {
    return attribution;
  }

  try {
    storage.setItem(
      REFERRAL_ATTRIBUTION_STORAGE_KEY,
      JSON.stringify(attribution),
    );
  } catch (error) {
    console.warn('[referral-attribution] failed to persist localStorage', error);
  }

  return attribution;
}

export function persistReferralAttribution({
  code,
  landingPath,
  now = Date.now(),
  storage = getLocalStorage(),
}: {
  code: string;
  landingPath: string;
  now?: number;
  storage?: ReferralStorage | null;
}): StoredReferralAttribution | null {
  const normalizedCode = normalizeReferralCode(code);
  if (!normalizedCode) {
    return null;
  }

  // First valid touch wins until it expires or is consumed by the backend.
  const existingAttribution = readReferralAttribution(storage, now);
  if (existingAttribution) {
    return existingAttribution;
  }

  return writeAttribution(
    createAttribution(normalizedCode, landingPath, now),
    storage,
  );
}

export function replaceReferralAttribution({
  code,
  landingPath,
  now = Date.now(),
  storage = getLocalStorage(),
}: {
  code: string;
  landingPath: string;
  now?: number;
  storage?: ReferralStorage | null;
}): StoredReferralAttribution | null {
  const normalizedCode = normalizeReferralCode(code);
  if (!normalizedCode) {
    return null;
  }

  return writeAttribution(
    createAttribution(normalizedCode, landingPath, now),
    storage,
  );
}

export function clearReferralAttribution(
  storage: ReferralStorage | null = getLocalStorage(),
): void {
  if (storage) {
    removeStoredValue(storage);
  }
}
