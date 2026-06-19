import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from '@/i18n/config';
import {
  buildCanonicalRedirectUrl,
  buildExternalRequestRedirectUrl,
} from '@/shared/lib/redirect-url';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
  localePrefix: 'always',
});

const ADMIN_PRIMARY_HOST = 'admin.cyber-vpn.net';
const ADMIN_REDIRECT_ONLY_HOST = 'admin.cyber-vpn.org';
const PUBLIC_PRIMARY_HOST = 'cyber-vpn.net';
const PUBLIC_WWW_HOST = 'www.cyber-vpn.net';
const CABINET_PRIMARY_HOST = 'my.cyber-vpn.net';
const ADMIN_ORIGIN = `https://${ADMIN_PRIMARY_HOST}`;
const PUBLIC_ORIGIN = SITE_URL;
const CABINET_ORIGIN = `https://${CABINET_PRIMARY_HOST}`;
const CABINET_REDIRECT_ALLOWED_HOSTS = new Set([
  CABINET_PRIMARY_HOST,
  'localhost',
  '127.0.0.1',
]);

const CABINET_ROUTE_SEGMENTS = new Set([
  'analytics',
  'dashboard',
  'delete-account',
  'monitoring',
  'partner',
  'payment-history',
  'referral',
  'servers',
  'settings',
  'subscriptions',
  'support',
  'users',
  'wallet',
]);

const AUTH_ROUTE_SEGMENTS = new Set([
  'forgot-password',
  'login',
  'magic-link',
  'oauth',
  'register',
  'reset-password',
  'telegram-link',
  'verify',
]);

const PUBLIC_ROUTE_SEGMENTS = new Set([
  'acceptable-use',
  'api',
  'audits',
  'compare',
  'contact',
  'cookie-policy',
  'devices',
  'docs',
  'download',
  'features',
  'guides',
  'help',
  'network',
  'pricing',
  'privacy',
  'privacy-policy',
  'refund-policy',
  'security',
  'status',
  'telegram-widget',
  'terms',
  'trust',
]);

function normalizeHostnameCandidate(candidate?: string | null): string | null {
  const host = candidate?.split(',')[0]?.trim();

  if (!host) {
    return null;
  }

  try {
    return new URL(`http://${host}`).hostname.toLowerCase().replace(/\.$/, '');
  } catch {
    return host.replace(/:\d+$/, '').toLowerCase().replace(/\.$/, '');
  }
}

function normalizedHostname(request: NextRequest): string {
  return (
    // In production proxy requests, nextUrl/Host can point at the internal
    // listener while X-Forwarded-Host carries the external authority.
    normalizeHostnameCandidate(request.headers.get('x-forwarded-host'))
    ?? normalizeHostnameCandidate(request.headers.get('host'))
    ?? normalizeHostnameCandidate(request.nextUrl.host)
    ?? request.nextUrl.hostname.toLowerCase()
  );
}

function getRouteSegment(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0];
  const hasLocale = locales.includes(firstSegment as (typeof locales)[number]);

  return hasLocale ? segments[1] ?? '' : firstSegment ?? '';
}

function getRequestLocale(pathname: string): string {
  const firstSegment = pathname.split('/').filter(Boolean)[0];
  return locales.includes(firstSegment as (typeof locales)[number])
    ? firstSegment
    : defaultLocale;
}

function getShortReferralCode(pathname: string): string | null {
  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0];
  const hasLocale = locales.includes(firstSegment as (typeof locales)[number]);
  const routeIndex = hasLocale ? 1 : 0;

  if (segments[routeIndex] !== 'r') {
    return null;
  }

  const rawCode = segments[routeIndex + 1];
  return rawCode ? decodeURIComponent(rawCode).trim() : null;
}

function getLegacyReferralCode(request: NextRequest, routeSegment: string): string | null {
  if (routeSegment !== 'referral') {
    return null;
  }

  return (
    request.nextUrl.searchParams.get('code') ||
    request.nextUrl.searchParams.get('ref') ||
    request.nextUrl.searchParams.get('referral')
  )?.trim() || null;
}

function buildReferralRegisterRedirectUrl(request: NextRequest, rawCode: string): URL {
  const locale = getRequestLocale(request.nextUrl.pathname);
  const target = new URL(`/${locale}/register`, CABINET_ORIGIN);
  target.searchParams.set('ref', rawCode);

  request.nextUrl.searchParams.forEach((value, key) => {
    if (key === 'code' || key === 'ref' || key === 'referral') {
      return;
    }
    target.searchParams.append(key, value);
  });

  return target;
}

/**
 * Next.js 16 proxy function for routing.
 *
 * SEC-01: Auth uses httpOnly cookies set with path="/api", so they are NOT
 * visible on page navigation requests. Auth protection for dashboard routes
 * is handled by the <AuthGuard> component in the (dashboard) layout, which
 * calls /auth/session (an /api path where the cookie IS sent) to verify the session.
 *
 * Per CLAUDE.md: "Do NOT put auth logic in proxy — use layouts or route
 * handlers instead."
 */
export function proxy(request: NextRequest) {
  const hostname = normalizedHostname(request);

  if (hostname === ADMIN_REDIRECT_ONLY_HOST) {
    return NextResponse.redirect(buildCanonicalRedirectUrl(request, ADMIN_ORIGIN));
  }

  const routeSegment = getRouteSegment(request.nextUrl.pathname);
  const shortReferralCode = getShortReferralCode(request.nextUrl.pathname);
  if (shortReferralCode) {
    return NextResponse.redirect(buildReferralRegisterRedirectUrl(request, shortReferralCode));
  }

  const legacyReferralCode = getLegacyReferralCode(request, routeSegment);
  if (legacyReferralCode) {
    return NextResponse.redirect(buildReferralRegisterRedirectUrl(request, legacyReferralCode));
  }

  if (
    (hostname === PUBLIC_PRIMARY_HOST || hostname === PUBLIC_WWW_HOST)
    && CABINET_ROUTE_SEGMENTS.has(routeSegment)
  ) {
    return NextResponse.redirect(buildCanonicalRedirectUrl(request, CABINET_ORIGIN));
  }

  if (hostname === CABINET_PRIMARY_HOST) {
    if (!routeSegment) {
      return NextResponse.redirect(
        buildExternalRequestRedirectUrl(request, CABINET_ORIGIN, {
          pathname: `/${defaultLocale}/dashboard`,
          allowedHosts: CABINET_REDIRECT_ALLOWED_HOSTS,
        }),
      );
    }

    if (
      PUBLIC_ROUTE_SEGMENTS.has(routeSegment)
      && !AUTH_ROUTE_SEGMENTS.has(routeSegment)
      && !CABINET_ROUTE_SEGMENTS.has(routeSegment)
    ) {
      return NextResponse.redirect(buildCanonicalRedirectUrl(request, PUBLIC_ORIGIN));
    }
  }

  return intlMiddleware(request);
}

export const config = {
  matcher: [
    '/((?!api|_next|_vercel|.*\\..*).*)',
  ],
};

export default proxy;
