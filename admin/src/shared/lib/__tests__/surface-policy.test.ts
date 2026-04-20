import { describe, expect, it } from 'vitest';
import { canAdminConsoleSurfaceAccess } from '../surface-policy';

describe('admin console surface policy', () => {
  it('keeps internal review and maker-checker controls on the admin surface only', () => {
    expect(canAdminConsoleSurfaceAccess('internal_review_tools')).toBe(true);
    expect(canAdminConsoleSurfaceAccess('maker_checker_controls')).toBe(true);
    expect(canAdminConsoleSurfaceAccess('storefront_checkout')).toBe(false);
    expect(canAdminConsoleSurfaceAccess('partner_workspace_modules')).toBe(false);
  });
});
