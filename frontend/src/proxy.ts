import { NextRequest } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from '@/i18n/config';

// i18n middleware
const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
  localePrefix: 'always',
});

/**
 * Next.js 16 proxy function for routing.
 *
 * Auth is handled client-side via Zustand store (tokens in localStorage).
 * Dashboard layout uses AuthGuard component to check isAuthenticated
 * and redirect to login if needed.
 */
export function proxy(request: NextRequest) {
  return intlMiddleware(request);
}

export const config = {
  matcher: [
    '/((?!api|_next|_vercel|.*\\..*).*)',
  ],
};

// Export default for backwards compatibility during migration
export default proxy;
