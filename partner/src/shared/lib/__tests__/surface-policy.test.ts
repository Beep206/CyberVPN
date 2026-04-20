import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  assertCurrentPartnerSurfaceCapability,
  canPartnerSurfaceAccess,
  resolveCurrentPartnerSurfaceFamily,
  resolvePartnerSurfaceFamilyFromHost,
} from '../surface-policy';

describe('partner surface policy', () => {
  beforeEach(() => {
    window.location.href = 'http://portal.localhost:3002/en-EN/dashboard';
  });

  afterEach(() => {
    window.location.href = 'http://portal.localhost:3002/en-EN/dashboard';
  });

  it('keeps workspace modules on portal but blocks admin-only controls', () => {
    expect(canPartnerSurfaceAccess('portal', 'workspace_navigation')).toBe(true);
    expect(canPartnerSurfaceAccess('portal', 'workspace_operator_modules')).toBe(true);
    expect(canPartnerSurfaceAccess('portal', 'internal_admin_moderation')).toBe(false);
    expect(canPartnerSurfaceAccess('portal', 'maker_checker_controls')).toBe(false);
  });

  it('keeps storefront limited to public commerce capabilities', () => {
    expect(canPartnerSurfaceAccess('storefront', 'storefront_public_routes')).toBe(true);
    expect(canPartnerSurfaceAccess('storefront', 'storefront_checkout')).toBe(true);
    expect(canPartnerSurfaceAccess('storefront', 'workspace_operator_modules')).toBe(false);
  });

  it('resolves the current surface family from the active host', () => {
    expect(resolveCurrentPartnerSurfaceFamily()).toBe('portal');
    expect(resolvePartnerSurfaceFamilyFromHost('storefront.localhost:3002')).toBe('storefront');
  });

  it('throws when portal code attempts to access maker-checker controls', () => {
    expect(() => assertCurrentPartnerSurfaceCapability('maker_checker_controls')).toThrow(
      /maker_checker_controls is not allowed on portal surface/i,
    );
  });
});
