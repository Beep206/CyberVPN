import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from '@/i18n/config';

// Routes that don't require authentication
const PUBLIC_ROUTES = [
  '/login',
  '/register',
  '/forgot-password',
  '/privacy-policy',
  '/terms',
  '/', // Landing page
  '/verify',
];

// Routes that are always public (static assets, API, etc.)
const ALWAYS_PUBLIC_PREFIXES = [
  '/api',
  '/_next',
  '/_vercel',
  '/static',
  '/favicon',
];

function isPublicRoute(pathname: string): boolean {
  // Check prefixes first
  if (ALWAYS_PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return true;
  }

  // Strip locale prefix for checking PUBLIC_ROUTES
  // Handles: /en-EN/login, /ru-RU/login, etc.
  let pathWithoutLocale = pathname.replace(/^\/[a-z]{2}-[A-Z]{2}/, '');

  // Strip trailing slash if present (except for root '/')
  if (pathWithoutLocale.length > 1 && pathWithoutLocale.endsWith('/')) {
    pathWithoutLocale = pathWithoutLocale.slice(0, -1);
  }

  return PUBLIC_ROUTES.includes(pathWithoutLocale) || PUBLIC_ROUTES.includes(pathname);
}

// i18n middleware
const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
  localePrefix: 'always',
});

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Always run i18n middleware first for locale handling
  const intlResponse = intlMiddleware(request);

  // Skip auth check for public routes
  if (isPublicRoute(pathname)) {
    return intlResponse;
  }

  // Check for access token cookie
  const accessToken = request.cookies.get('access_token')?.value;

  // Dev bypass (for development only)
  const isDevBypass = request.cookies.get('DEV_BYPASS_AUTH')?.value === 'true';
  if (isDevBypass && process.env.NODE_ENV === 'development') {
    intlResponse.headers.set('X-Dev-Auth-Bypass', 'true');
    return intlResponse;
  }

  // No token - redirect to login
  if (!accessToken) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Token exists - allow request (actual validation happens in API calls)
  // Note: Full JWT validation should happen in layout/server components
  // proxy.ts is for routing only per Next.js 16 guidelines
  return intlResponse;
}

export const config = {
  matcher: [
    '/((?!api|_next|_vercel|.*\\..*).*)',
  ],
};

// Export default for backwards compatibility during migration
export default proxy;
