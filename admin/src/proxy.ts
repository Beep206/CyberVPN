import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from '@/i18n/config';

const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
  localePrefix: 'always',
});

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
  const localeLikePathMatch = request.nextUrl.pathname.match(/^\/([a-z]{2,3}-[A-Z]{2})(\/.*)?$/);
  const locale = localeLikePathMatch?.[1];

  if (locale && !locales.includes(locale as (typeof locales)[number])) {
    const normalizedUrl = request.nextUrl.clone();
    const remainder = localeLikePathMatch?.[2] ?? '';
    normalizedUrl.pathname = remainder ? `/${defaultLocale}${remainder}` : `/${defaultLocale}/login`;

    return NextResponse.redirect(normalizedUrl);
  }

  const localizedRootMatch = request.nextUrl.pathname.match(/^\/([a-z]{2,3}-[A-Z]{2})\/?$/);
  const localizedRootLocale = localizedRootMatch?.[1];

  if (localizedRootLocale && locales.includes(localizedRootLocale as (typeof locales)[number])) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = `/${localizedRootLocale}/login`;
    loginUrl.search = '';

    return NextResponse.redirect(loginUrl);
  }

  return intlMiddleware(request);
}

export const config = {
  matcher: [
    '/((?!api|_next|_vercel|.*\\..*).*)',
  ],
};

export default proxy;
