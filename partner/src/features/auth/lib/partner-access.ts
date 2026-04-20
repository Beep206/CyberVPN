import type { User } from '@/lib/api/auth';
import { resolvePartnerSurfaceContext } from '@/features/storefront-shell/lib/runtime';

export const ACCESS_DENIED_ERROR_CODE = 'partner_access_denied';
export const PARTNER_PORTAL_REALM_KEY = 'partner';
export const PARTNER_PORTAL_AUDIENCE = 'cybervpn:partner';
export const PARTNER_PORTAL_PRINCIPAL_TYPE = 'partner_operator';

type PartnerPortalIdentity = Pick<
  User,
  'role' | 'auth_realm_key' | 'audience' | 'principal_type'
>;

function isPartnerPortalIdentity(
  value: PartnerPortalIdentity | User['role'] | string | null | undefined,
): value is PartnerPortalIdentity {
  return typeof value === 'object' && value !== null;
}

function hasLegacyRoleFallback(role: User['role'] | string | null | undefined): boolean {
  return process.env.NODE_ENV !== 'production' && typeof role === 'string' && role.length > 0;
}

export function hasPartnerPortalAccess(
  identity: PartnerPortalIdentity | User['role'] | string | null | undefined,
): boolean {
  if (!isPartnerPortalIdentity(identity)) {
    return hasLegacyRoleFallback(identity);
  }

  const hasRuntimeIdentity =
    typeof identity.auth_realm_key === 'string'
    || typeof identity.audience === 'string'
    || typeof identity.principal_type === 'string';

  if (hasRuntimeIdentity) {
    return (
      identity.auth_realm_key === PARTNER_PORTAL_REALM_KEY
      && identity.audience === PARTNER_PORTAL_AUDIENCE
      && identity.principal_type === PARTNER_PORTAL_PRINCIPAL_TYPE
    );
  }

  return hasLegacyRoleFallback(identity.role);
}

export function isPartnerPortalUser(
  user: PartnerPortalIdentity | null | undefined,
): boolean {
  return hasPartnerPortalAccess(user);
}

export function resolvePartnerAuthRealmKeyFromHost(
  rawHost: string | null | undefined,
): string {
  const surfaceContext = resolvePartnerSurfaceContext(rawHost);

  if (surfaceContext.family === 'portal') {
    return PARTNER_PORTAL_REALM_KEY;
  }

  return surfaceContext.authRealmKey;
}

export function buildLocalizedAccessDeniedLoginPath(locale: string): string {
  return `/${locale}/login?error=${ACCESS_DENIED_ERROR_CODE}`;
}
