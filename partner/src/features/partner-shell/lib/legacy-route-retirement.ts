export type LegacyAdminRouteTarget =
  | '/dashboard'
  | '/programs'
  | '/codes'
  | '/conversions'
  | '/finance'
  | '/team'
  | '/compliance'
  | '/integrations'
  | '/settings';

export interface LegacyAdminRouteRetirement {
  legacyPrefix: `/_legacy-admin-routes${string}`;
  targetPath: LegacyAdminRouteTarget;
}

const LEGACY_ADMIN_ROOT = '/_legacy-admin-routes';

export const LEGACY_ADMIN_ROUTE_RETIREMENTS = [
  { legacyPrefix: '/_legacy-admin-routes/commerce', targetPath: '/finance' },
  { legacyPrefix: '/_legacy-admin-routes/customers', targetPath: '/conversions' },
  { legacyPrefix: '/_legacy-admin-routes/governance/admin-invites', targetPath: '/team' },
  { legacyPrefix: '/_legacy-admin-routes/governance', targetPath: '/compliance' },
  { legacyPrefix: '/_legacy-admin-routes/growth/invite-codes', targetPath: '/codes' },
  { legacyPrefix: '/_legacy-admin-routes/growth/promo-codes', targetPath: '/codes' },
  { legacyPrefix: '/_legacy-admin-routes/growth/referrals', targetPath: '/conversions' },
  { legacyPrefix: '/_legacy-admin-routes/growth', targetPath: '/programs' },
  { legacyPrefix: '/_legacy-admin-routes/infrastructure', targetPath: '/dashboard' },
  { legacyPrefix: '/_legacy-admin-routes/integrations', targetPath: '/integrations' },
  { legacyPrefix: '/_legacy-admin-routes/security', targetPath: '/settings' },
] as const satisfies readonly LegacyAdminRouteRetirement[];

function stripLocale(pathname: string): string {
  return pathname.replace(/^\/[a-z]{2,3}-[A-Z]{2}(?=\/|$)/, '') || '/';
}

function normalizePathname(pathname: string): string {
  const withoutLocale = stripLocale(pathname);

  if (withoutLocale === '/') {
    return withoutLocale;
  }

  return withoutLocale.replace(/\/+$/, '');
}

function matchesLegacyPrefix(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

export function getRetiredLegacyAdminRouteTarget(
  pathname: string,
): LegacyAdminRouteTarget | null {
  const normalizedPathname = normalizePathname(pathname);

  if (normalizedPathname === LEGACY_ADMIN_ROOT) {
    return '/dashboard';
  }

  const retirement = LEGACY_ADMIN_ROUTE_RETIREMENTS.find(({ legacyPrefix }) => (
    matchesLegacyPrefix(normalizedPathname, legacyPrefix)
  ));

  return retirement?.targetPath ?? null;
}
