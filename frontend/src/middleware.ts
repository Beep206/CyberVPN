import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from '@/i18n/config';

// Middleware wrapper to handle Auth Bypass
export default async function middleware(request: any) {
    const isDevBypass = request.cookies.get('DEV_BYPASS_AUTH')?.value === 'true';

    // If bypass is on, we might skip upcoming auth checks
    // For now, we just proceed, but in a real auth guard, we would return next() immediately.
    // Since createMiddleware returns a response, we just return it.

    // Original intl middleware
    const response = createMiddleware({
        locales,
        defaultLocale,
        localePrefix: 'always'
    })(request);

    if (isDevBypass) {
        response.headers.set('X-Dev-Auth-Bypass', 'true');
    }

    return response;
}

export const config = {
    matcher: [
        // Match all pathnames except for
        // - … if they start with `/api`, `/_next` or `/_vercel`
        // - … the ones containing a dot (e.g. `favicon.ico`)
        '/((?!api|_next|_vercel|.*\\..*).*)',
        // However, match all pathnames within `/users`, optionally with a locale prefix
        // '/([\\w-]+)?/users/(.+)'
    ]
};
