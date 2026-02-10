import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from '@/i18n/config';

const AUTH_COOKIE = 'access_token';

const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
  localePrefix: 'always',
});

/**
 * Next.js 16 proxy function for routing.
 *
 * SEC-01: Auth uses httpOnly cookies. The proxy performs a fast-path cookie
 * presence check on dashboard routes — this is NOT a security boundary.
 * The backend remains the authority; AuthGuard is the client-side fallback.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Fast-path: redirect to login if accessing dashboard without auth cookie.
  // Match /{locale}/(dashboard)/... or /{locale}/dashboard/...
  const isDashboardRoute = /^\/[a-z]{2,3}(-[A-Z]{2})?(\/(dashboard|\(dashboard\)))/.test(pathname);

  if (isDashboardRoute && !request.cookies.has(AUTH_COOKIE)) {
    // Extract locale from path (first segment)
    const locale = pathname.split('/')[1] || defaultLocale;
    const redirectUrl = new URL(`/${locale}/login`, request.url);
    redirectUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(redirectUrl, 307);
  }

  return intlMiddleware(request);
}

export const config = {
  matcher: [
    '/((?!api|_next|_vercel|.*\\..*).*)',
  ],
};

export default proxy;
