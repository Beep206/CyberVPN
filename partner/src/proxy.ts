import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from '@/i18n/config';
import {
  isLocalizedRootPath,
  isPortalWorkspacePath,
  isRetiredGenericPortalSectionPath,
  isStorefrontPublicPath,
  getDefaultPartnerStorefrontHost,
  getCanonicalPartnerSurfaceHost,
  isKnownPartnerSurfaceHost,
  type PartnerSurfaceContext,
  resolvePartnerSurfaceContext,
} from '@/features/storefront-shell/lib/runtime';
import { getRetiredLegacyAdminRouteTarget } from '@/features/partner-shell/lib/legacy-route-retirement';
import { buildExternalRequestRedirectUrl } from '@/shared/lib/redirect-url';
import { canPartnerSurfaceAccess } from '@/shared/lib/surface-policy';

const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
  localePrefix: 'always',
});

const LOCAL_SURFACE_HOSTS = [
  'localhost',
  '127.0.0.1',
  'portal.localhost',
  'storefront.localhost',
] as const;

function getHostname(host: string): string {
  try {
    return new URL(`http://${host}`).hostname.toLowerCase().replace(/\.$/, '');
  } catch {
    return host.replace(/:\d+$/, '').toLowerCase().replace(/\.$/, '');
  }
}

function isLocalSurfaceHost(host: string): boolean {
  const hostname = getHostname(host);
  return LOCAL_SURFACE_HOSTS.includes(hostname as (typeof LOCAL_SURFACE_HOSTS)[number]);
}

function getSurfaceRedirectUrl(
  request: NextRequest,
  surfaceContext: PartnerSurfaceContext,
  pathname: string,
  options: { preserveSearch?: boolean } = {},
): URL {
  const canonicalHost = getCanonicalPartnerSurfaceHost(surfaceContext);
  const fallbackOrigin = `${isLocalSurfaceHost(canonicalHost) ? 'http' : 'https'}://${canonicalHost}`;
  const allowedHosts = new Set<string>([canonicalHost, ...LOCAL_SURFACE_HOSTS]);

  return buildExternalRequestRedirectUrl(request, fallbackOrigin, {
    pathname,
    preserveSearch: options.preserveSearch,
    allowedHosts,
  });
}

function resolveProxySurfaceContext(request: NextRequest): PartnerSurfaceContext {
  const forwardedHost = request.headers.get('x-forwarded-host');
  if (forwardedHost) {
    if (isKnownPartnerSurfaceHost(forwardedHost)) {
      return resolvePartnerSurfaceContext(forwardedHost);
    }

    return resolvePartnerSurfaceContext(getDefaultPartnerStorefrontHost());
  }

  const host = request.headers.get('host');
  if (isKnownPartnerSurfaceHost(host)) {
    return resolvePartnerSurfaceContext(host);
  }

  return resolvePartnerSurfaceContext(getDefaultPartnerStorefrontHost());
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
  const surfaceContext = resolveProxySurfaceContext(request);
  const localeLikePathMatch = request.nextUrl.pathname.match(/^\/([a-z]{2,3}-[A-Z]{2})(\/.*)?$/);
  const locale = localeLikePathMatch?.[1];

  if (locale && !locales.includes(locale as (typeof locales)[number])) {
    const remainder = localeLikePathMatch?.[2] ?? '';

    return NextResponse.redirect(
      getSurfaceRedirectUrl(
        request,
        surfaceContext,
        remainder ? `/${defaultLocale}${remainder}` : `/${defaultLocale}/login`,
        { preserveSearch: true },
      ),
    );
  }

  const retiredLegacyAdminTarget = locale
    ? getRetiredLegacyAdminRouteTarget(request.nextUrl.pathname)
    : null;

  if (retiredLegacyAdminTarget) {
    return NextResponse.redirect(
      getSurfaceRedirectUrl(
        request,
        surfaceContext,
        canPartnerSurfaceAccess(surfaceContext.family, 'workspace_navigation')
          ? `/${locale}${retiredLegacyAdminTarget}`
          : `/${locale}`,
        { preserveSearch: false },
      ),
    );
  }

  if (
    surfaceContext.family === 'portal'
    && locale
    && isRetiredGenericPortalSectionPath(request.nextUrl.pathname)
  ) {
    const response = new NextResponse(null, { status: 404 });
    response.headers.set('Cache-Control', 'no-store');
    return response;
  }

  if (
    surfaceContext.family === 'portal'
    && isLocalizedRootPath(request.nextUrl.pathname)
    && locale
    && locales.includes(locale as (typeof locales)[number])
  ) {
    return NextResponse.redirect(
      getSurfaceRedirectUrl(request, surfaceContext, `/${locale}/login`, {
        preserveSearch: false,
      }),
    );
  }

  if (
    !canPartnerSurfaceAccess(surfaceContext.family, 'workspace_navigation')
    && isPortalWorkspacePath(request.nextUrl.pathname)
    && locale
  ) {
    return NextResponse.redirect(
      getSurfaceRedirectUrl(request, surfaceContext, `/${locale}`, {
        preserveSearch: false,
      }),
    );
  }

  if (
    !canPartnerSurfaceAccess(surfaceContext.family, 'storefront_public_routes')
    && isStorefrontPublicPath(request.nextUrl.pathname)
    && locale
  ) {
    return NextResponse.redirect(
      getSurfaceRedirectUrl(request, surfaceContext, `/${locale}/login`, {
        preserveSearch: false,
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
