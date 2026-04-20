import {
  resolvePartnerSurfaceContext,
  type PartnerSurfaceFamily,
} from '@/features/storefront-shell/lib/runtime';

export type PartnerSurfaceCapability =
  | 'workspace_navigation'
  | 'workspace_operator_modules'
  | 'storefront_public_routes'
  | 'storefront_checkout'
  | 'internal_admin_routes'
  | 'internal_admin_moderation'
  | 'maker_checker_controls';

const PARTNER_SURFACE_POLICY: Record<
  PartnerSurfaceFamily,
  Record<PartnerSurfaceCapability, boolean>
> = {
  portal: {
    workspace_navigation: true,
    workspace_operator_modules: true,
    storefront_public_routes: false,
    storefront_checkout: false,
    internal_admin_routes: false,
    internal_admin_moderation: false,
    maker_checker_controls: false,
  },
  storefront: {
    workspace_navigation: false,
    workspace_operator_modules: false,
    storefront_public_routes: true,
    storefront_checkout: true,
    internal_admin_routes: false,
    internal_admin_moderation: false,
    maker_checker_controls: false,
  },
};

export function canPartnerSurfaceAccess(
  surface: PartnerSurfaceFamily,
  capability: PartnerSurfaceCapability,
): boolean {
  return PARTNER_SURFACE_POLICY[surface][capability];
}

export function resolvePartnerSurfaceFamilyFromHost(
  rawHost: string | null | undefined,
): PartnerSurfaceFamily {
  return resolvePartnerSurfaceContext(rawHost).family;
}

export function resolveCurrentPartnerSurfaceFamily(): PartnerSurfaceFamily {
  if (typeof window === 'undefined') {
    return 'portal';
  }

  return resolvePartnerSurfaceFamilyFromHost(window.location.host);
}

export function assertCurrentPartnerSurfaceCapability(
  capability: PartnerSurfaceCapability,
): void {
  const surface = resolveCurrentPartnerSurfaceFamily();

  if (canPartnerSurfaceAccess(surface, capability)) {
    return;
  }

  throw new Error(
    `Partner surface policy violation: ${capability} is not allowed on ${surface} surface`,
  );
}
