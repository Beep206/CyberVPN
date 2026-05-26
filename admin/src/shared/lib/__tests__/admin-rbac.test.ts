import { describe, expect, it } from 'vitest';
import {
  ADMIN_PERMISSIONS,
  ADMIN_ROLES,
  getAdminRolePermissions,
  hasAdminAccess,
  hasAdminPermission,
  isAdminRole,
} from '../admin-rbac';

describe('admin-rbac', () => {
  it('matches the backend admin role contract used by auth/session', () => {
    expect(ADMIN_ROLES).toEqual([
      'viewer',
      'support',
      'operator',
      'finance',
      'admin',
      'super_admin',
      'owner/super_admin',
    ]);

    for (const role of ADMIN_ROLES) {
      expect(isAdminRole(role)).toBe(true);
      expect(hasAdminAccess(role)).toBe(true);
    }

    expect(hasAdminAccess('user')).toBe(false);
    expect(hasAdminAccess('legacy_root')).toBe(false);
    expect(hasAdminAccess(null)).toBe(false);
  });

  it('gives owner and super admin the complete frontend permission set', () => {
    expect(getAdminRolePermissions('owner/super_admin')).toEqual(ADMIN_PERMISSIONS);
    expect(getAdminRolePermissions('super_admin')).toEqual(ADMIN_PERMISSIONS);
  });

  it('keeps support, operator, finance, and viewer permissions separated', () => {
    expect(hasAdminPermission('support', 'user_read')).toBe(true);
    expect(hasAdminPermission('support', 'vpn_credential_regenerate')).toBe(true);
    expect(hasAdminPermission('support', 'payment_read')).toBe(false);

    expect(hasAdminPermission('operator', 'subscription_create')).toBe(true);
    expect(hasAdminPermission('operator', 'payment_read')).toBe(false);
    expect(hasAdminPermission('operator', 'user_update')).toBe(false);

    expect(hasAdminPermission('finance', 'payment_read')).toBe(true);
    expect(hasAdminPermission('finance', 'audit_read')).toBe(true);
    expect(hasAdminPermission('finance', 'server_read')).toBe(false);

    expect(hasAdminPermission('viewer', 'view_analytics')).toBe(true);
    expect(hasAdminPermission('viewer', 'user_update')).toBe(false);
  });
});
