import { normalizeAuthLocale } from '@/features/auth/lib/redirect-path';

const LOCALE_PREFIX_RE = /^\/[a-z]{2,3}-[A-Z]{2}(?=\/|$)/;
const MINIAPP_FALLBACK_PATH = '/miniapp/home';

type ReplaceRouter = {
  replace: (href: string) => void;
};

function stripLocalePrefix(pathname: string): string {
  return pathname.replace(LOCALE_PREFIX_RE, '') || '/';
}

export function localizeMiniAppPath(path: string, locale: string): string {
  if (!path.startsWith('/') || path.startsWith('//')) {
    return `/${normalizeAuthLocale(locale)}${MINIAPP_FALLBACK_PATH}`;
  }

  const parsed = new URL(path, 'https://cyber-vpn.net');
  const pathWithoutLocale = stripLocalePrefix(parsed.pathname);
  const miniappPath = pathWithoutLocale.startsWith('/miniapp/')
    ? pathWithoutLocale
    : MINIAPP_FALLBACK_PATH;
  const currentRelease = typeof window !== 'undefined'
    ? new URLSearchParams(window.location.search).get('release')
    : null;

  if (currentRelease && !parsed.searchParams.has('release')) {
    parsed.searchParams.set('release', currentRelease);
  }

  return `/${normalizeAuthLocale(locale)}${miniappPath}${parsed.search}${parsed.hash}`;
}

function isAtTargetPath(targetPath: string): boolean {
  if (typeof window === 'undefined') {
    return true;
  }

  const target = new URL(targetPath, window.location.origin);
  const currentPath = stripLocalePrefix(window.location.pathname);
  const targetPathWithoutLocale = stripLocalePrefix(target.pathname);
  const searchMatches = target.search ? window.location.search === target.search : true;
  return currentPath === targetPathWithoutLocale && searchMatches;
}

export function replaceMiniAppPath(
  router: ReplaceRouter,
  path: string,
  locale: string,
  options: { fallbackDelayMs?: number } = {},
): void {
  const fallbackDelayMs = options.fallbackDelayMs ?? 800;
  router.replace(path);

  if (typeof window === 'undefined' || !window.Telegram?.WebApp) {
    return;
  }

  const localizedTarget = localizeMiniAppPath(path, locale);
  window.setTimeout(() => {
    if (!isAtTargetPath(localizedTarget)) {
      window.location.assign(localizedTarget);
    }
  }, fallbackDelayMs);
}
