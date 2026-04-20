export type AdminConsoleSurfaceCapability =
  | 'internal_review_tools'
  | 'maker_checker_controls'
  | 'storefront_checkout'
  | 'partner_workspace_modules';

const ADMIN_CONSOLE_SURFACE_POLICY: Record<AdminConsoleSurfaceCapability, boolean> = {
  internal_review_tools: true,
  maker_checker_controls: true,
  storefront_checkout: false,
  partner_workspace_modules: false,
};

export function canAdminConsoleSurfaceAccess(
  capability: AdminConsoleSurfaceCapability,
): boolean {
  return ADMIN_CONSOLE_SURFACE_POLICY[capability];
}
