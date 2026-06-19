import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from '@/i18n/config';
import { buildExternalRequestRedirectUrl } from '@/shared/lib/redirect-url';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
  localePrefix: 'always',
});

const ADMIN_REDIRECT_ALLOWED_HOSTS = new Set([
  new URL(SITE_URL).hostname,
  'localhost',
  '127.0.0.1',
]);

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
    const remainder = localeLikePathMatch?.[2] ?? '';

    return NextResponse.redirect(
      buildExternalRequestRedirectUrl(request, SITE_URL, {
        pathname: remainder ? `/${defaultLocale}${remainder}` : `/${defaultLocale}/login`,
        allowedHosts: ADMIN_REDIRECT_ALLOWED_HOSTS,
      }),
    );
  }

  const localizedRootMatch = request.nextUrl.pathname.match(/^\/([a-z]{2,3}-[A-Z]{2})\/?$/);
  const localizedRootLocale = localizedRootMatch?.[1];

  if (localizedRootLocale && locales.includes(localizedRootLocale as (typeof locales)[number])) {
    return NextResponse.redirect(
      buildExternalRequestRedirectUrl(request, SITE_URL, {
        pathname: `/${localizedRootLocale}/login`,
        preserveSearch: false,
        allowedHosts: ADMIN_REDIRECT_ALLOWED_HOSTS,
      }),
    );
  }

  return intlMiddleware(request);
}

export const config = {
  matcher: [
    '/((?!api|_next|_vercel|.*\\..*).*)',
  ],
};

export default proxy;
