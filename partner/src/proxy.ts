import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from '@/i18n/config';
import {
  isLocalizedRootPath,
  isPortalWorkspacePath,
  isStorefrontPublicPath,
  resolvePartnerSurfaceContext,
} from '@/features/storefront-shell/lib/runtime';
import { canPartnerSurfaceAccess } from '@/shared/lib/surface-policy';

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
  const surfaceContext = resolvePartnerSurfaceContext(
    request.headers.get('x-forwarded-host') ?? request.headers.get('host'),
  );
  const localeLikePathMatch = request.nextUrl.pathname.match(/^\/([a-z]{2,3}-[A-Z]{2})(\/.*)?$/);
  const locale = localeLikePathMatch?.[1];

  if (locale && !locales.includes(locale as (typeof locales)[number])) {
    const normalizedUrl = request.nextUrl.clone();
    const remainder = localeLikePathMatch?.[2] ?? '';
    normalizedUrl.pathname = remainder ? `/${defaultLocale}${remainder}` : `/${defaultLocale}/login`;

    return NextResponse.redirect(normalizedUrl);
  }

  if (
    surfaceContext.family === 'portal'
    && isLocalizedRootPath(request.nextUrl.pathname)
    && locale
    && locales.includes(locale as (typeof locales)[number])
  ) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = `/${locale}/login`;
    loginUrl.search = '';

    return NextResponse.redirect(loginUrl);
  }

  if (
    !canPartnerSurfaceAccess(surfaceContext.family, 'workspace_navigation')
    && isPortalWorkspacePath(request.nextUrl.pathname)
    && locale
  ) {
    const storefrontUrl = request.nextUrl.clone();
    storefrontUrl.pathname = `/${locale}`;
    storefrontUrl.search = '';

    return NextResponse.redirect(storefrontUrl);
  }

  if (
    !canPartnerSurfaceAccess(surfaceContext.family, 'storefront_public_routes')
    && isStorefrontPublicPath(request.nextUrl.pathname)
    && locale
  ) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = `/${locale}/login`;
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
