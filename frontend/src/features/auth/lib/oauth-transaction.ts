import { createHmac, timingSafeEqual } from 'node:crypto';

import type { OAuthProvider } from '@/lib/api/auth';
import { getSafeRedirectPath, normalizeAuthLocale } from './redirect-path';

export const OAUTH_TRANSACTION_COOKIE = 'oauth_tx';
export const OAUTH_TRANSACTION_TTL_SECONDS = 10 * 60;

const OAUTH_TRANSACTION_VERSION = 1 as const;
const DEV_OAUTH_TRANSACTION_SECRET = 'cybervpn-dev-oauth-transaction-secret';
const WEB_OAUTH_PROVIDERS = new Set<OAuthProvider>([
  'google',
  'github',
  'discord',
  'facebook',
  'apple',
  'microsoft',
  'twitter',
]);

interface OAuthTransactionPayload {
  v: typeof OAUTH_TRANSACTION_VERSION;
  provider: OAuthProvider;
  locale: string;
  returnTo: string;
  issuedAt: number;
}

export interface OAuthTransaction {
  provider: OAuthProvider;
  locale: string;
  returnTo: string;
}

export interface OAuthTransactionCookie extends OAuthTransaction {
  cookieValue: string;
}

export const oauthTransactionCookieOptions = {
  httpOnly: true,
  maxAge: OAUTH_TRANSACTION_TTL_SECONDS,
  path: '/',
  sameSite: 'lax' as const,
  secure: process.env.NODE_ENV === 'production',
};

function getOAuthTransactionSecret(): string {
  const configuredSecret = process.env.OAUTH_TRANSACTION_SECRET?.trim();
  if (configuredSecret) {
    return configuredSecret;
  }

  if (process.env.NODE_ENV === 'production') {
    throw new Error('OAUTH_TRANSACTION_SECRET must be configured in production.');
  }

  return DEV_OAUTH_TRANSACTION_SECRET;
}

function signPayload(encodedPayload: string): string {
  return createHmac('sha256', getOAuthTransactionSecret())
    .update(encodedPayload)
    .digest('base64url');
}

function isValidOAuthProvider(provider: string): provider is OAuthProvider {
  return WEB_OAUTH_PROVIDERS.has(provider as OAuthProvider);
}

export function isSupportedWebOAuthProvider(provider: string): provider is OAuthProvider {
  return isValidOAuthProvider(provider);
}

export function createOAuthTransactionCookieValue(
  provider: OAuthProvider,
  localeInput: string | null | undefined,
  rawReturnTo: string | null,
): OAuthTransactionCookie {
  const locale = normalizeAuthLocale(localeInput);
  const returnTo = getSafeRedirectPath(rawReturnTo, locale);

  const payload: OAuthTransactionPayload = {
    v: OAUTH_TRANSACTION_VERSION,
    provider,
    locale,
    returnTo,
    issuedAt: Date.now(),
  };

  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const signature = signPayload(encodedPayload);

  return {
    provider,
    locale,
    returnTo,
    cookieValue: `${encodedPayload}.${signature}`,
  };
}

export function parseOAuthTransactionCookieValue(cookieValue: string | undefined | null): OAuthTransaction | null {
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
    ) as Partial<OAuthTransactionPayload>;

    if (payload.v !== OAUTH_TRANSACTION_VERSION) {
      return null;
    }

    if (!payload.provider || !isValidOAuthProvider(payload.provider)) {
      return null;
    }

    if (typeof payload.issuedAt !== 'number') {
      return null;
    }

    if (Date.now() - payload.issuedAt > OAUTH_TRANSACTION_TTL_SECONDS * 1000) {
      return null;
    }

    const locale = normalizeAuthLocale(payload.locale);
    const returnTo = getSafeRedirectPath(
      typeof payload.returnTo === 'string' ? payload.returnTo : null,
      locale,
    );

    return {
      provider: payload.provider,
      locale,
      returnTo,
    };
  } catch {
    return null;
  }
}
