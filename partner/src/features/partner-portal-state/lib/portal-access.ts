import {
  PARTNER_SECTION_SLUGS,
  type PartnerSectionSlug,
} from '@/features/partner-shell/config/section-registry';
import type {
  PartnerPortalState,
  PartnerWorkspaceRole,
} from '@/features/partner-portal-state/lib/portal-state';
import {
  getPartnerRouteVisibility,
  type PartnerRouteKey,
  type PartnerSectionVisibility,
} from '@/features/partner-portal-state/lib/portal-visibility';

export type PartnerRouteAccessLevel =
  | 'none'
  | 'read'
  | 'write'
  | 'admin';

type PartnerPortalAccessState = PartnerPortalState & {
  currentPermissionKeys?: readonly string[];
};

const DEFAULT_ALL_ROLES_READ = {
  workspace_owner: 'read',
  workspace_admin: 'read',
  finance_manager: 'read',
  analyst: 'read',
  traffic_manager: 'read',
  support_manager: 'read',
  technical_manager: 'read',
  legal_compliance_manager: 'read',
} as const satisfies Record<PartnerWorkspaceRole, PartnerRouteAccessLevel>;

const ROUTE_ROLE_ACCESS: Record<
  PartnerRouteKey,
  Partial<Record<PartnerWorkspaceRole, PartnerRouteAccessLevel>>
> = {
  dashboard: DEFAULT_ALL_ROLES_READ,
  application: {
    workspace_owner: 'admin',
    workspace_admin: 'write',
    finance_manager: 'read',
    analyst: 'read',
    traffic_manager: 'write',
    support_manager: 'read',
    technical_manager: 'read',
    legal_compliance_manager: 'write',
  },
  organization: {
    workspace_owner: 'admin',
    workspace_admin: 'write',
    finance_manager: 'write',
    analyst: 'read',
    traffic_manager: 'write',
    support_manager: 'read',
    technical_manager: 'write',
    legal_compliance_manager: 'write',
  },
  team: {
    workspace_owner: 'admin',
    workspace_admin: 'write',
  },
  programs: {
    workspace_owner: 'admin',
    workspace_admin: 'write',
    finance_manager: 'read',
    analyst: 'read',
    traffic_manager: 'write',
    support_manager: 'read',
    technical_manager: 'read',
    legal_compliance_manager: 'read',
  },
  legal: {
    workspace_owner: 'admin',
    workspace_admin: 'read',
    finance_manager: 'read',
    analyst: 'read',
    traffic_manager: 'read',
    support_manager: 'read',
    legal_compliance_manager: 'write',
  },
  codes: {
    workspace_owner: 'admin',
    workspace_admin: 'write',
    finance_manager: 'read',
    analyst: 'read',
    traffic_manager: 'write',
    support_manager: 'read',
    technical_manager: 'read',
  },
  campaigns: {
    workspace_owner: 'admin',
    workspace_admin: 'write',
    analyst: 'read',
    traffic_manager: 'write',
    support_manager: 'read',
    technical_manager: 'read',
    legal_compliance_manager: 'read',
  },
  conversions: DEFAULT_ALL_ROLES_READ,
  analytics: DEFAULT_ALL_ROLES_READ,
  finance: {
    workspace_owner: 'read',
    workspace_admin: 'read',
    finance_manager: 'write',
    analyst: 'read',
    support_manager: 'read',
    legal_compliance_manager: 'read',
  },
  compliance: {
    workspace_owner: 'admin',
    workspace_admin: 'write',
    finance_manager: 'read',
    analyst: 'read',
    traffic_manager: 'write',
    support_manager: 'read',
    technical_manager: 'read',
    legal_compliance_manager: 'write',
  },
  integrations: {
    workspace_owner: 'admin',
    workspace_admin: 'write',
    analyst: 'read',
    traffic_manager: 'write',
    technical_manager: 'write',
  },
  cases: {
    workspace_owner: 'admin',
    workspace_admin: 'write',
    finance_manager: 'write',
    traffic_manager: 'write',
    support_manager: 'write',
    technical_manager: 'read',
    legal_compliance_manager: 'write',
  },
  notifications: DEFAULT_ALL_ROLES_READ,
  settings: {
    workspace_owner: 'write',
    workspace_admin: 'write',
    finance_manager: 'write',
    analyst: 'write',
    traffic_manager: 'write',
    support_manager: 'write',
    technical_manager: 'write',
    legal_compliance_manager: 'write',
  },
  reseller: {
    workspace_owner: 'admin',
    workspace_admin: 'write',
    finance_manager: 'read',
    support_manager: 'read',
    technical_manager: 'write',
  },
};

const ROUTE_PERMISSION_REQUIREMENTS: Record<PartnerRouteKey, readonly string[]> = {
  dashboard: ['workspace_read'],
  application: ['workspace_read'],
  organization: ['workspace_read'],
  team: ['membership_read'],
  programs: ['workspace_read'],
  legal: ['workspace_read'],
  codes: ['codes_read'],
  campaigns: ['codes_read'],
  conversions: ['earnings_read'],
  analytics: ['earnings_read'],
  finance: ['earnings_read'],
  compliance: ['workspace_read'],
  integrations: ['workspace_read'],
  cases: ['workspace_read'],
  notifications: ['workspace_read'],
  settings: ['workspace_read'],
  reseller: ['codes_read'],
};

function downgradeAccessByVisibility(
  roleAccess: PartnerRouteAccessLevel,
  visibility: PartnerSectionVisibility,
): PartnerRouteAccessLevel {
  if (visibility === 'hidden' || roleAccess === 'none') {
    return 'none';
  }

  if (visibility === 'read') {
    return 'read';
  }

  if (visibility === 'task' && roleAccess === 'admin') {
    return 'write';
  }

  return roleAccess;
}

export function getPartnerRoleRouteAccess(
  route: PartnerRouteKey,
  state: PartnerPortalAccessState,
): PartnerRouteAccessLevel {
  const visibility = getPartnerRouteVisibility(route, state);
  const roleAccess = ROUTE_ROLE_ACCESS[route][state.workspaceRole] ?? 'none';
  const permissionKeys = state.currentPermissionKeys ?? [];

  if (
    permissionKeys.length > 0
    && !ROUTE_PERMISSION_REQUIREMENTS[route].some((permission) => permissionKeys.includes(permission))
  ) {
    return 'none';
  }

  return downgradeAccessByVisibility(roleAccess, visibility);
}

export function canPartnerRouteAccess(
  route: PartnerRouteKey,
  state: PartnerPortalAccessState,
): boolean {
  return getPartnerRoleRouteAccess(route, state) !== 'none';
}

export function countPartnerAccessibleSections(
  state: PartnerPortalAccessState,
): number {
  const routes: PartnerRouteKey[] = ['dashboard', ...PARTNER_SECTION_SLUGS];

  return routes.filter((route) => canPartnerRouteAccess(route, state)).length;
}

export function getPartnerRouteFromHref(href: '/dashboard' | `/${PartnerSectionSlug}`): PartnerRouteKey {
  return href === '/dashboard' ? 'dashboard' : href.slice(1) as PartnerSectionSlug;
}
