import type { OAuthProvider } from '@/lib/api/auth';

export const DEFAULT_AUTH_LOCALE = 'en-EN';
export const OAUTH_RESULT_COOKIE = 'oauth_result';
export const OAUTH_RESULT_TTL_SECONDS = 5 * 60;

const LOCALE_RE = /^\/([a-z]{2,3}-[A-Z]{2})(?:\/|$)/;
const AUTH_ROUTE_RE = /^\/(?:[a-z]{2,3}-[A-Z]{2}\/)?(?:login|register|magic-link|forgot-password|reset-password|verify|oauth\/callback|telegram-link)(?:\/|$)/;
const OAUTH_PROVIDERS = new Set<OAuthProvider>([
  'google',
  'github',
  'discord',
  'facebook',
  'apple',
  'microsoft',
  'twitter',
  'telegram',
]);

export const oauthResultCookieOptions = {
  httpOnly: false,
  maxAge: OAUTH_RESULT_TTL_SECONDS,
  path: '/',
  sameSite: 'lax' as const,
  secure: process.env.NODE_ENV === 'production',
};

export function isSupportedOAuthProvider(value: string | null | undefined): value is OAuthProvider {
  return Boolean(value && OAUTH_PROVIDERS.has(value as OAuthProvider));
}

export function getLocaleFromPathname(pathname: string): string {
  const match = pathname.match(LOCALE_RE);
  return match ? match[1] : DEFAULT_AUTH_LOCALE;
}

export function isPublicAuthRoute(pathname: string): boolean {
  return AUTH_ROUTE_RE.test(pathname);
}

export function shouldBootstrapAuthSession(pathname: string): boolean {
  return !isPublicAuthRoute(pathname);
}

export function buildLocalizedLoginRedirect(pathname: string): string {
  const locale = getLocaleFromPathname(pathname);
  const redirectTarget = isPublicAuthRoute(pathname) ? `/${locale}/dashboard` : pathname;
  return `/${locale}/login?redirect=${encodeURIComponent(redirectTarget)}`;
}

export function consumeOAuthResultCookie(): OAuthProvider | null {
  if (typeof document === 'undefined') {
    return null;
  }

  const cookieEntry = document.cookie
    .split('; ')
    .find((entry) => entry.startsWith(`${OAUTH_RESULT_COOKIE}=`));

  if (!cookieEntry) {
    return null;
  }

  const rawValue = decodeURIComponent(cookieEntry.split('=').slice(1).join('='));
  document.cookie = `${OAUTH_RESULT_COOKIE}=; Max-Age=0; Path=/; SameSite=Lax`;

  return isSupportedOAuthProvider(rawValue) ? rawValue : null;
}
