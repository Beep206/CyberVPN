import { createHmac, timingSafeEqual } from 'node:crypto';

import { getDefaultPostLoginPath, getSafeRedirectPath, normalizeAuthLocale } from './redirect-path';

export const PENDING_2FA_COOKIE = 'pending_2fa';
export const PENDING_2FA_TTL_SECONDS = 15 * 60;

const PENDING_2FA_VERSION = 1 as const;
const DEV_PENDING_2FA_SECRET = 'cybervpn-dev-pending-2fa-secret';

interface PendingTwoFactorPayload {
  v: typeof PENDING_2FA_VERSION;
  token: string;
  locale: string;
  returnTo: string;
  isNewUser: boolean;
  issuedAt: number;
}

export interface PendingTwoFactorTransaction {
  token: string;
  locale: string;
  returnTo: string;
  isNewUser: boolean;
}

export interface PendingTwoFactorCookie extends PendingTwoFactorTransaction {
  cookieValue: string;
}

export const pendingTwoFactorCookieOptions = {
  httpOnly: true,
  maxAge: PENDING_2FA_TTL_SECONDS,
  path: '/',
  sameSite: 'lax' as const,
  secure: process.env.NODE_ENV === 'production',
};

function getPendingTwoFactorSecret(): string {
  const configuredSecret =
    process.env.PENDING_2FA_SECRET?.trim()
    || process.env.OAUTH_TRANSACTION_SECRET?.trim();

  if (configuredSecret) {
    return configuredSecret;
  }

  if (process.env.NODE_ENV === 'production') {
    throw new Error('PENDING_2FA_SECRET or OAUTH_TRANSACTION_SECRET must be configured in production.');
  }

  return DEV_PENDING_2FA_SECRET;
}

function signPayload(encodedPayload: string): string {
  return createHmac('sha256', getPendingTwoFactorSecret())
    .update(encodedPayload)
    .digest('base64url');
}

export function createPendingTwoFactorCookieValue(
  token: string,
  localeInput: string | null | undefined,
  rawReturnTo: string | null,
  isNewUser = false,
): PendingTwoFactorCookie {
  const locale = normalizeAuthLocale(localeInput);
  const returnTo = getSafeRedirectPath(rawReturnTo, locale) || getDefaultPostLoginPath(locale);

  const payload: PendingTwoFactorPayload = {
    v: PENDING_2FA_VERSION,
    token,
    locale,
    returnTo,
    isNewUser,
    issuedAt: Date.now(),
  };

  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const signature = signPayload(encodedPayload);

  return {
    token,
    locale,
    returnTo,
    isNewUser,
    cookieValue: `${encodedPayload}.${signature}`,
  };
}

export function parsePendingTwoFactorCookieValue(cookieValue: string | undefined | null): PendingTwoFactorTransaction | null {
  if (!cookieValue) {
    return null;
  }

  const [encodedPayload, signature] = cookieValue.split('.');
  if (!encodedPayload || !signature) {
    return null;
  }

  const expectedSignature = signPayload(encodedPayload);
  const signatureBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expectedSignature);

  if (
    signatureBuffer.length !== expectedBuffer.length
    || !timingSafeEqual(signatureBuffer, expectedBuffer)
  ) {
    return null;
  }

  try {
    const payload = JSON.parse(
      Buffer.from(encodedPayload, 'base64url').toString('utf8'),
    ) as Partial<PendingTwoFactorPayload>;

    if (payload.v !== PENDING_2FA_VERSION) {
      return null;
    }

    if (typeof payload.token !== 'string' || !payload.token.trim()) {
      return null;
    }

    if (typeof payload.issuedAt !== 'number') {
      return null;
    }

    if (Date.now() - payload.issuedAt > PENDING_2FA_TTL_SECONDS * 1000) {
      return null;
    }

    const locale = normalizeAuthLocale(payload.locale);
    const returnTo = getSafeRedirectPath(
      typeof payload.returnTo === 'string' ? payload.returnTo : null,
      locale,
    );

    return {
      token: payload.token,
      locale,
      returnTo,
      isNewUser: Boolean(payload.isNewUser),
    };
  } catch {
    return null;
  }
}
