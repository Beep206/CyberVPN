export const REFERRAL_ATTRIBUTION_COOKIE_NAME = 'cybervpn_referral_attribution';
export const REFERRAL_ATTRIBUTION_STORAGE_KEY = 'cybervpn.referral-attribution.v1';
export const REFERRAL_ATTRIBUTION_TTL_SECONDS = 30 * 24 * 60 * 60;
export const REFERRAL_ATTRIBUTION_TTL_MS = REFERRAL_ATTRIBUTION_TTL_SECONDS * 1000;

const REFERRAL_CODE_PATTERN = /^[A-Z0-9_-]{4,12}$/;
const REFERRAL_QUERY_KEYS = ['ref', 'referral', 'referral_code'] as const;

export function normalizeReferralCode(value: string | null | undefined): string | null {
  const normalized = value?.trim().toUpperCase() ?? '';
  return REFERRAL_CODE_PATTERN.test(normalized) ? normalized : null;
}

function isLegacyReferralLanding(pathname: string): boolean {
  return /(?:^|\/)referral\/?$/.test(pathname);
}

export function extractReferralCode(
  pathname: string,
  searchParams: Pick<URLSearchParams, 'get'>,
): string | null {
  for (const key of REFERRAL_QUERY_KEYS) {
    const code = normalizeReferralCode(searchParams.get(key));
    if (code) {
      return code;
    }
  }

  // `code` is intentionally accepted only on the legacy referral landing.
  // OAuth callbacks also use `?code=...` and must never become referrals.
  if (isLegacyReferralLanding(pathname)) {
    return normalizeReferralCode(searchParams.get('code'));
  }

  return null;
}
