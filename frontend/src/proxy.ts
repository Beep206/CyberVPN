import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from '@/i18n/config';
import {
  buildCanonicalRedirectUrl,
  buildExternalRequestRedirectUrl,
} from '@/shared/lib/redirect-url';
import { SITE_URL } from '@/shared/lib/seo-route-policy';
import {
  CABINET_ALLOWED_PREFIXES,
  getLocalizedRouteSegment,
  isCabinetRouteSegment,
} from '@/shared/lib/cabinet-routes';

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
const ADMIN_ORIGIN = `https://${ADMIN_PRIMARY_HOST}`;
const PUBLIC_ORIGIN = SITE_URL;
const CABINET_ORIGIN = `https://${CABINET_PRIMARY_HOST}`;
const CUSTOMER_SITE_RUNTIME_TTL_MS = 15_000;
const CUSTOMER_SITE_RUNTIME_TIMEOUT_MS = 500;
const CABINET_REDIRECT_ALLOWED_HOSTS = new Set([
  CABINET_PRIMARY_HOST,
  'localhost',
  '127.0.0.1',
]);
const REFERRAL_REDIRECT_CAMPAIGN_KEYS = new Set([
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_term',
  'utm_content',
  'gclid',
  'fbclid',
  'click_id',
  'sub_id',
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

const AUTH_REDIRECT_PRESERVE_QUERY_KEYS = new Set([
  ...REFERRAL_REDIRECT_CAMPAIGN_KEYS,
  'ref',
  'referral',
  'code',
  'state',
  'scope',
  'authuser',
  'prompt',
]);

type CustomerSiteMode = 'full_site' | 'cabinet_only' | 'maintenance';

type CustomerSiteRuntimeSnapshot = {
  mode: CustomerSiteMode;
  version: number;
  publicHosts: readonly string[];
  cabinetHosts: readonly string[];
  cabinetDestinationPath: string;
  allowedPathPrefixes: readonly string[];
  cabinetAllowedPrefixes: readonly string[];
  cabinetMarketingRouteAction: 'redirect_public' | 'allow' | 'not_found';
  publicMarketingDestinationPath: string;
  legalPathPrefixes: readonly string[];
  operationalPathPrefixes: readonly string[];
  preserveQueryKeys: readonly string[];
};

type CachedCustomerSiteRuntime = {
  expiresAt: number;
  snapshot: CustomerSiteRuntimeSnapshot;
};

const DEFAULT_CUSTOMER_SITE_RUNTIME: CustomerSiteRuntimeSnapshot = {
  mode: 'full_site',
  version: 1,
  publicHosts: [PUBLIC_PRIMARY_HOST, PUBLIC_WWW_HOST],
  cabinetHosts: [CABINET_PRIMARY_HOST],
  cabinetDestinationPath: '/dashboard',
  allowedPathPrefixes: [
    '/login',
    '/register',
    '/verify',
    '/verify-email',
    '/reset-password',
    '/magic-link',
    '/oauth',
    '/telegram-link',
    '/legal',
    '/r/',
    '/p/',
    '/.well-known/',
  ],
  cabinetAllowedPrefixes: [
    ...CABINET_ALLOWED_PREFIXES,
    '/login',
    '/register',
    '/verify',
    '/verify-email',
    '/forgot-password',
    '/reset-password',
    '/magic-link',
    '/oauth',
    '/telegram-link',
  ],
  cabinetMarketingRouteAction: 'redirect_public',
  publicMarketingDestinationPath: '/',
  legalPathPrefixes: [
    '/acceptable-use',
    '/cookie-policy',
    '/privacy',
    '/privacy-policy',
    '/refund-policy',
    '/terms',
  ],
  operationalPathPrefixes: [
    '/status',
    '/telegram-widget',
    '/.well-known',
  ],
  preserveQueryKeys: [
    'ref',
    'referral',
    'utm_source',
    'utm_medium',
    'utm_campaign',
    'utm_content',
    'utm_term',
  ],
};

let cachedCustomerSiteRuntime: CachedCustomerSiteRuntime | null = null;
let lastKnownGoodCustomerSiteRuntime: CustomerSiteRuntimeSnapshot | null = null;

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
    // In production proxy requests, nextUrl/Host can point at the internal
    // listener while X-Forwarded-Host carries the external authority.
    normalizeHostnameCandidate(request.headers.get('x-forwarded-host'))
    ?? normalizeHostnameCandidate(request.headers.get('host'))
    ?? normalizeHostnameCandidate(request.nextUrl.host)
    ?? request.nextUrl.hostname.toLowerCase()
  );
}

function getRouteSegment(pathname: string): string {
  return getLocalizedRouteSegment(pathname);
}

function getRequestLocaleFromPathname(pathname: string): string | null {
  const firstSegment = pathname.split('/').filter(Boolean)[0];
  return locales.includes(firstSegment as (typeof locales)[number])
    ? firstSegment
    : null;
}

function isSupportedLocale(value: string | null | undefined): value is (typeof locales)[number] {
  return locales.includes(value as (typeof locales)[number]);
}

function resolveLocaleFromAcceptLanguage(header: string | null): string | null {
  if (!header) {
    return null;
  }

  const preferences = header
    .split(',')
    .map((part) => {
      const [language, ...params] = part.trim().split(';');
      const qParam = params.find((param) => param.trim().startsWith('q='));
      const q = qParam ? Number(qParam.split('=')[1]) : 1;
      return { language: language.trim(), q: Number.isFinite(q) ? q : 0 };
    })
    .filter((item) => item.language)
    .sort((a, b) => b.q - a.q);

  for (const item of preferences) {
    const exact = locales.find((locale) => locale.toLowerCase() === item.language.toLowerCase());
    if (exact) {
      return exact;
    }

    const languagePrefix = item.language.split('-')[0]?.toLowerCase();
    const prefixed = locales.find((locale) => locale.toLowerCase().startsWith(`${languagePrefix}-`));
    if (prefixed) {
      return prefixed;
    }
  }

  return null;
}

function resolvePreferredLocale(request: NextRequest): string {
  const pathnameLocale = getRequestLocaleFromPathname(request.nextUrl.pathname);
  if (pathnameLocale) {
    return pathnameLocale;
  }

  const cookieLocale = request.cookies.get('NEXT_LOCALE')?.value;
  if (isSupportedLocale(cookieLocale)) {
    return cookieLocale;
  }

  return resolveLocaleFromAcceptLanguage(request.headers.get('accept-language')) ?? defaultLocale;
}

function isNextInternalNavigationRequest(request: NextRequest): boolean {
  const accept = request.headers.get('accept')?.toLowerCase() ?? '';
  const purpose = request.headers.get('purpose')?.toLowerCase() ?? '';
  const secFetchMode = request.headers.get('sec-fetch-mode')?.toLowerCase() ?? '';
  const secFetchDest = request.headers.get('sec-fetch-dest')?.toLowerCase() ?? '';

  return (
    request.nextUrl.searchParams.has('_rsc')
    || request.headers.get('rsc') === '1'
    || request.headers.has('next-router-state-tree')
    || request.headers.has('next-router-prefetch')
    || request.headers.has('x-nextjs-data')
    || accept.includes('text/x-component')
    || purpose === 'prefetch'
    || (secFetchMode === 'cors' && secFetchDest === 'empty')
  );
}

function isCrossOriginTarget(request: NextRequest, target: URL): boolean {
  const sourceHost = normalizedHostname(request);
  const targetHost = normalizeHostnameCandidate(target.host);
  return Boolean(targetHost && targetHost !== sourceHost);
}

function redirectOrInternalNotFound(request: NextRequest, target: URL): NextResponse {
  if (isNextInternalNavigationRequest(request) && isCrossOriginTarget(request, target)) {
    return new NextResponse(null, { status: 404 });
  }

  return NextResponse.redirect(target);
}

function getUnlocalizedPathname(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0];
  if (!locales.includes(firstSegment as (typeof locales)[number])) {
    return pathname || '/';
  }

  const unlocalized = `/${segments.slice(1).join('/')}`;
  return unlocalized === '/' ? '/' : unlocalized.replace(/\/$/, '') || '/';
}

function getShortReferralCode(pathname: string): string | null {
  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0];
  const hasLocale = locales.includes(firstSegment as (typeof locales)[number]);
  const routeIndex = hasLocale ? 1 : 0;

  if (segments[routeIndex] !== 'r') {
    return null;
  }

  const rawCode = segments[routeIndex + 1];
  return rawCode ? decodeURIComponent(rawCode).trim() : null;
}

function getPartnerAttributionToken(pathname: string): {
  isLocalized: boolean;
  token: string;
} | null {
  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0];
  const isLocalized = locales.includes(firstSegment as (typeof locales)[number]);
  const routeIndex = isLocalized ? 1 : 0;

  if (segments[routeIndex] !== 'p') {
    return null;
  }

  const rawToken = segments[routeIndex + 1];
  const token = rawToken ? decodeURIComponent(rawToken).trim() : '';
  return token ? { isLocalized, token } : null;
}

function getLegacyReferralCode(request: NextRequest, routeSegment: string): string | null {
  if (routeSegment !== 'referral') {
    return null;
  }

  return (
    request.nextUrl.searchParams.get('code') ||
    request.nextUrl.searchParams.get('ref') ||
    request.nextUrl.searchParams.get('referral')
  )?.trim() || null;
}

function buildReferralRegisterRedirectUrl(request: NextRequest, rawCode: string): URL {
  const locale = resolvePreferredLocale(request);
  const target = new URL(`/${locale}/register`, CABINET_ORIGIN);
  target.searchParams.set('ref', rawCode);

  request.nextUrl.searchParams.forEach((value, key) => {
    if (REFERRAL_REDIRECT_CAMPAIGN_KEYS.has(key)) {
      target.searchParams.append(key, value);
    }
  });

  return target;
}

function buildPartnerAttributionCanonicalUrl(request: NextRequest, token: string): URL {
  const target = new URL(`/p/${encodeURIComponent(token)}`, PUBLIC_ORIGIN);
  request.nextUrl.searchParams.forEach((value, key) => {
    target.searchParams.append(key, value);
  });
  return target;
}

function normalizeCustomerSiteMode(value: unknown): CustomerSiteMode {
  return value === 'cabinet_only' || value === 'maintenance' ? value : 'full_site';
}

function fallbackCustomerSiteRuntimeSnapshot(): CustomerSiteRuntimeSnapshot {
  return {
    ...DEFAULT_CUSTOMER_SITE_RUNTIME,
    mode: normalizeCustomerSiteMode(process.env.CUSTOMER_SITE_MODE_FALLBACK),
  };
}

function normalizeStringList(value: unknown, fallback: readonly string[]): readonly string[] {
  if (!Array.isArray(value)) {
    return fallback;
  }

  const normalized = value
    .filter((item): item is string => typeof item === 'string')
    .map((item) => item.trim())
    .filter(Boolean);

  return normalized.length > 0 ? normalized : fallback;
}

function normalizeSafePathList(value: unknown, fallback: readonly string[]): readonly string[] {
  if (!Array.isArray(value)) {
    return fallback;
  }

  const normalized = value
    .filter((item): item is string => typeof item === 'string')
    .map((item) => item.trim())
    .filter((item) => item.startsWith('/') && !item.startsWith('//'))
    .slice(0, 100);

  return normalized.length > 0 ? normalized : fallback;
}

function normalizeSafePath(value: unknown, fallback: string): string {
  if (typeof value !== 'string') {
    return fallback;
  }

  const trimmed = value.trim();
  return trimmed.startsWith('/') && !trimmed.startsWith('//') ? trimmed : fallback;
}

function normalizePositiveVersion(value: unknown): number {
  const parsed = typeof value === 'number' || typeof value === 'string'
    ? Number(value)
    : Number.NaN;
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

function normalizeCabinetMarketingRouteAction(
  value: unknown,
): CustomerSiteRuntimeSnapshot['cabinetMarketingRouteAction'] {
  return value === 'allow' || value === 'not_found' || value === 'redirect_public'
    ? value
    : 'redirect_public';
}

function normalizeCustomerSiteRuntimeSnapshot(payload: unknown): CustomerSiteRuntimeSnapshot {
  const fallback = fallbackCustomerSiteRuntimeSnapshot();
  if (typeof payload !== 'object' || payload === null) {
    return fallback;
  }

  const site = (payload as { site?: unknown }).site;
  if (typeof site !== 'object' || site === null) {
    return fallback;
  }

  const siteRecord = site as Record<string, unknown>;
  const mode = normalizeCustomerSiteMode(
    siteRecord.customer_site_mode ?? (siteRecord.cabinet_only === true ? 'cabinet_only' : undefined),
  );

  return {
    mode,
    version: normalizePositiveVersion(siteRecord.version),
    publicHosts: normalizeStringList(siteRecord.public_hosts, fallback.publicHosts),
    cabinetHosts: normalizeStringList(siteRecord.cabinet_hosts, fallback.cabinetHosts),
    cabinetDestinationPath: normalizeSafePath(
      siteRecord.cabinet_destination_path,
      fallback.cabinetDestinationPath,
    ),
    allowedPathPrefixes: normalizeSafePathList(
      siteRecord.allowed_path_prefixes,
      fallback.allowedPathPrefixes,
    ),
    cabinetAllowedPrefixes: normalizeSafePathList(
      siteRecord.cabinet_allowed_prefixes,
      fallback.cabinetAllowedPrefixes,
    ),
    cabinetMarketingRouteAction: normalizeCabinetMarketingRouteAction(
      siteRecord.cabinet_marketing_route_action,
    ),
    publicMarketingDestinationPath: normalizeSafePath(
      siteRecord.public_marketing_destination_path,
      fallback.publicMarketingDestinationPath,
    ),
    legalPathPrefixes: normalizeSafePathList(
      siteRecord.legal_path_prefixes,
      fallback.legalPathPrefixes,
    ),
    operationalPathPrefixes: normalizeSafePathList(
      siteRecord.operational_path_prefixes,
      fallback.operationalPathPrefixes,
    ),
    preserveQueryKeys: normalizeStringList(siteRecord.preserve_query_keys, fallback.preserveQueryKeys),
  };
}

function resolveInternalApiOrigin(): string | null {
  const raw = (
    process.env.API_INTERNAL_ORIGIN
    || process.env.API_URL
    || process.env.NEXT_PUBLIC_API_URL
    || ''
  ).trim();
  if (!raw) {
    return null;
  }

  try {
    const parsed = new URL(raw);
    if ((parsed.protocol !== 'http:' && parsed.protocol !== 'https:') || parsed.username || parsed.password) {
      return null;
    }

    return parsed.origin;
  } catch {
    return null;
  }
}

async function fetchCustomerSiteRuntimeSnapshot(): Promise<CustomerSiteRuntimeSnapshot> {
  const now = Date.now();
  if (cachedCustomerSiteRuntime && cachedCustomerSiteRuntime.expiresAt > now) {
    return cachedCustomerSiteRuntime.snapshot;
  }

  const apiOrigin = resolveInternalApiOrigin();
  if (!apiOrigin) {
    return lastKnownGoodCustomerSiteRuntime ?? fallbackCustomerSiteRuntimeSnapshot();
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), CUSTOMER_SITE_RUNTIME_TIMEOUT_MS);
  try {
    const response = await fetch(`${apiOrigin}/api/v1/client/capabilities`, {
      cache: 'no-store',
      headers: { accept: 'application/json' },
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`Customer site runtime fetch failed with ${response.status}`);
    }

    const snapshot = normalizeCustomerSiteRuntimeSnapshot(await response.json());
    cachedCustomerSiteRuntime = {
      expiresAt: now + CUSTOMER_SITE_RUNTIME_TTL_MS,
      snapshot,
    };
    lastKnownGoodCustomerSiteRuntime = snapshot;
    return snapshot;
  } catch {
    return lastKnownGoodCustomerSiteRuntime ?? fallbackCustomerSiteRuntimeSnapshot();
  } finally {
    clearTimeout(timeout);
  }
}

function firstConfiguredHost(hosts: readonly string[], fallback: string): string {
  const normalized = hosts
    .map((host) => normalizeHostnameCandidate(host))
    .find((host): host is string => Boolean(host));

  return normalized ?? fallback;
}

function matchesConfiguredHost(hostname: string, hosts: readonly string[]): boolean {
  return hosts
    .map((host) => normalizeHostnameCandidate(host))
    .some((host) => host === hostname);
}

function localizedRuntimePath(locale: string, path: string): string {
  const safePath = normalizeSafePath(path, DEFAULT_CUSTOMER_SITE_RUNTIME.cabinetDestinationPath);
  const segments = safePath.split('/').filter(Boolean);
  const firstSegment = segments[0];

  if (locales.includes(firstSegment as (typeof locales)[number])) {
    return safePath;
  }

  return `/${locale}${safePath === '/' ? '' : safePath}`;
}

function buildWhitelistedRedirectUrl(
  request: NextRequest,
  origin: string,
  pathname: string,
  allowedQueryKeys: ReadonlySet<string>,
): URL {
  const target = new URL(pathname, origin);
  request.nextUrl.searchParams.forEach((value, key) => {
    if (allowedQueryKeys.has(key)) {
      target.searchParams.append(key, value);
    }
  });
  return target;
}

function getRuntimePreserveQueryKeys(snapshot: CustomerSiteRuntimeSnapshot): ReadonlySet<string> {
  return new Set(snapshot.preserveQueryKeys);
}

function isAllowedByRuntimePrefix(pathname: string, prefixes: readonly string[]): boolean {
  return prefixes.some((prefix) => {
    const normalizedPrefix = normalizeSafePath(prefix, '/').replace(/\/$/, '') || '/';
    return pathname === normalizedPrefix || pathname.startsWith(`${normalizedPrefix}/`);
  });
}

function isCabinetOnlyLegalOrOperationalRoute(
  unlocalizedPathname: string,
  snapshot: CustomerSiteRuntimeSnapshot,
): boolean {
  return (
    isAllowedByRuntimePrefix(unlocalizedPathname, snapshot.legalPathPrefixes)
    || isAllowedByRuntimePrefix(unlocalizedPathname, snapshot.operationalPathPrefixes)
  );
}

function buildMaintenanceRedirect(
  request: NextRequest,
  snapshot: CustomerSiteRuntimeSnapshot,
  hostname: string,
): NextResponse | null {
  if (snapshot.mode !== 'maintenance') {
    return null;
  }

  const unlocalizedPathname = getUnlocalizedPathname(request.nextUrl.pathname);
  const inScopeHost =
    matchesConfiguredHost(hostname, snapshot.publicHosts)
    || matchesConfiguredHost(hostname, snapshot.cabinetHosts);
  if (!inScopeHost || isCabinetOnlyLegalOrOperationalRoute(unlocalizedPathname, snapshot)) {
    return null;
  }

  const locale = resolvePreferredLocale(request);
  const publicHost = firstConfiguredHost(snapshot.publicHosts, PUBLIC_PRIMARY_HOST);
  const target = buildWhitelistedRedirectUrl(
    request,
    `https://${publicHost}`,
    `/${locale}/status`,
    getRuntimePreserveQueryKeys(snapshot),
  );
  target.searchParams.set('mode', 'maintenance');
  target.searchParams.set('source', 'site_mode');
  return redirectOrInternalNotFound(request, target);
}

function buildCabinetOnlyRedirect(
  request: NextRequest,
  snapshot: CustomerSiteRuntimeSnapshot,
  hostname: string,
  routeSegment: string,
): NextResponse | null {
  if (snapshot.mode !== 'cabinet_only') {
    return null;
  }

  const isPublicHost = matchesConfiguredHost(hostname, snapshot.publicHosts);
  const isCabinetHost = matchesConfiguredHost(hostname, snapshot.cabinetHosts);
  if (!isPublicHost && !isCabinetHost) {
    return null;
  }

  const unlocalizedPathname = getUnlocalizedPathname(request.nextUrl.pathname);
  if (isCabinetOnlyLegalOrOperationalRoute(unlocalizedPathname, snapshot)) {
    return null;
  }

  if (isCabinetHost) {
    if (isAllowedByRuntimePrefix(unlocalizedPathname, snapshot.cabinetAllowedPrefixes)) {
      return null;
    }

    if (snapshot.cabinetMarketingRouteAction === 'allow') {
      return null;
    }

    if (snapshot.cabinetMarketingRouteAction === 'not_found') {
      return new NextResponse(null, { status: 404 });
    }

    const locale = resolvePreferredLocale(request);
    const publicHost = firstConfiguredHost(snapshot.publicHosts, PUBLIC_PRIMARY_HOST);
    return redirectOrInternalNotFound(
      request,
      buildWhitelistedRedirectUrl(
        request,
        `https://${publicHost}`,
        localizedRuntimePath(locale, snapshot.publicMarketingDestinationPath),
        getRuntimePreserveQueryKeys(snapshot),
      ),
    );
  }

  if (isAllowedByRuntimePrefix(unlocalizedPathname, snapshot.allowedPathPrefixes)) {
    if (isPublicHost && AUTH_ROUTE_SEGMENTS.has(routeSegment)) {
      const cabinetHost = firstConfiguredHost(snapshot.cabinetHosts, CABINET_PRIMARY_HOST);
      const locale = resolvePreferredLocale(request);
      const targetPathname = getRequestLocaleFromPathname(request.nextUrl.pathname) === null
        ? localizedRuntimePath(locale, unlocalizedPathname)
        : request.nextUrl.pathname;
      return redirectOrInternalNotFound(
        request,
        buildWhitelistedRedirectUrl(
          request,
          `https://${cabinetHost}`,
          targetPathname,
          AUTH_REDIRECT_PRESERVE_QUERY_KEYS,
        ),
      );
    }

    return null;
  }

  const locale = resolvePreferredLocale(request);
  const cabinetHost = firstConfiguredHost(snapshot.cabinetHosts, CABINET_PRIMARY_HOST);
  return redirectOrInternalNotFound(
    request,
    buildWhitelistedRedirectUrl(
      request,
      `https://${cabinetHost}`,
      localizedRuntimePath(locale, snapshot.cabinetDestinationPath),
      getRuntimePreserveQueryKeys(snapshot),
    ),
  );
}

export function resetCustomerSiteRuntimeCacheForTests(): void {
  cachedCustomerSiteRuntime = null;
  lastKnownGoodCustomerSiteRuntime = null;
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
export async function proxy(request: NextRequest) {
  const hostname = normalizedHostname(request);

  if (hostname === ADMIN_REDIRECT_ONLY_HOST) {
    return redirectOrInternalNotFound(request, buildCanonicalRedirectUrl(request, ADMIN_ORIGIN));
  }

  const routeSegment = getRouteSegment(request.nextUrl.pathname);
  const partnerAttribution = getPartnerAttributionToken(request.nextUrl.pathname);
  if (partnerAttribution) {
    if (
      partnerAttribution.isLocalized
      || (hostname !== PUBLIC_PRIMARY_HOST && hostname !== PUBLIC_WWW_HOST)
    ) {
      return redirectOrInternalNotFound(
        request,
        buildPartnerAttributionCanonicalUrl(request, partnerAttribution.token),
      );
    }
    return NextResponse.next();
  }

  const shortReferralCode = getShortReferralCode(request.nextUrl.pathname);
  if (shortReferralCode) {
    return redirectOrInternalNotFound(request, buildReferralRegisterRedirectUrl(request, shortReferralCode));
  }

  const legacyReferralCode = getLegacyReferralCode(request, routeSegment);
  if (legacyReferralCode) {
    return redirectOrInternalNotFound(request, buildReferralRegisterRedirectUrl(request, legacyReferralCode));
  }

  const siteRuntime = await fetchCustomerSiteRuntimeSnapshot();
  const maintenanceRedirect = buildMaintenanceRedirect(
    request,
    siteRuntime,
    hostname,
  );
  if (maintenanceRedirect) {
    return maintenanceRedirect;
  }

  if (
    (hostname === PUBLIC_PRIMARY_HOST || hostname === PUBLIC_WWW_HOST)
    && isCabinetRouteSegment(routeSegment)
  ) {
    return redirectOrInternalNotFound(request, buildCanonicalRedirectUrl(request, CABINET_ORIGIN));
  }

  const cabinetOnlyRedirect = buildCabinetOnlyRedirect(request, siteRuntime, hostname, routeSegment);
  if (cabinetOnlyRedirect) {
    return cabinetOnlyRedirect;
  }

  if (hostname === CABINET_PRIMARY_HOST) {
    if (!routeSegment) {
      return redirectOrInternalNotFound(
        request,
        buildExternalRequestRedirectUrl(request, CABINET_ORIGIN, {
          pathname: `/${resolvePreferredLocale(request)}/dashboard`,
          allowedHosts: CABINET_REDIRECT_ALLOWED_HOSTS,
        }),
      );
    }

    if (
      siteRuntime.mode !== 'cabinet_only'
      && siteRuntime.mode !== 'maintenance'
      && PUBLIC_ROUTE_SEGMENTS.has(routeSegment)
      && !AUTH_ROUTE_SEGMENTS.has(routeSegment)
      && !isCabinetRouteSegment(routeSegment)
    ) {
      return redirectOrInternalNotFound(request, buildCanonicalRedirectUrl(request, PUBLIC_ORIGIN));
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
