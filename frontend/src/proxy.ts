import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from '@/i18n/config';

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
    // In local/runtime proxy requests, nextUrl can point at the listener while
    // Host carries the externally requested authority that isolation depends on.
    normalizeHostnameCandidate(request.headers.get('host'))
    ?? normalizeHostnameCandidate(request.headers.get('x-forwarded-host'))
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
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.protocol = 'https:';
    redirectUrl.hostname = ADMIN_PRIMARY_HOST;
    return NextResponse.redirect(redirectUrl);
  }

  const routeSegment = getRouteSegment(request.nextUrl.pathname);

  if (
    (hostname === PUBLIC_PRIMARY_HOST || hostname === PUBLIC_WWW_HOST)
    && CABINET_ROUTE_SEGMENTS.has(routeSegment)
  ) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.protocol = 'https:';
    redirectUrl.hostname = CABINET_PRIMARY_HOST;
    return NextResponse.redirect(redirectUrl);
  }

  if (hostname === CABINET_PRIMARY_HOST) {
    if (!routeSegment) {
      const redirectUrl = request.nextUrl.clone();
      redirectUrl.protocol = 'https:';
      redirectUrl.hostname = CABINET_PRIMARY_HOST;
      redirectUrl.pathname = `/${defaultLocale}/dashboard`;
      return NextResponse.redirect(redirectUrl);
    }

    if (
      PUBLIC_ROUTE_SEGMENTS.has(routeSegment)
      && !AUTH_ROUTE_SEGMENTS.has(routeSegment)
      && !CABINET_ROUTE_SEGMENTS.has(routeSegment)
    ) {
      const redirectUrl = request.nextUrl.clone();
      redirectUrl.protocol = 'https:';
      redirectUrl.hostname = PUBLIC_PRIMARY_HOST;
      return NextResponse.redirect(redirectUrl);
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
