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
    expect(hasAdminPermission('support', 'support_ticket_read')).toBe(true);
    expect(hasAdminPermission('support', 'notification_broadcast_create')).toBe(false);
    expect(hasAdminPermission('support', 'payment_read')).toBe(false);

    expect(hasAdminPermission('operator', 'subscription_create')).toBe(true);
    expect(hasAdminPermission('operator', 'support_ticket_read')).toBe(false);
    expect(hasAdminPermission('operator', 'notification_broadcast_create')).toBe(false);
    expect(hasAdminPermission('operator', 'payment_read')).toBe(false);
    expect(hasAdminPermission('operator', 'user_update')).toBe(false);

    expect(hasAdminPermission('finance', 'payment_read')).toBe(true);
    expect(hasAdminPermission('finance', 'audit_read')).toBe(true);
    expect(hasAdminPermission('finance', 'support_ticket_read')).toBe(false);
    expect(hasAdminPermission('finance', 'server_read')).toBe(false);

    expect(hasAdminPermission('viewer', 'view_analytics')).toBe(true);
    expect(hasAdminPermission('viewer', 'notification_broadcast_create')).toBe(false);
    expect(hasAdminPermission('viewer', 'support_ticket_read')).toBe(false);
    expect(hasAdminPermission('viewer', 'user_update')).toBe(false);
  });

  it('grants notification broadcast creation only to admin-level roles', () => {
    for (const role of ['admin', 'super_admin', 'owner/super_admin'] as const) {
      expect(hasAdminPermission(role, 'notification_broadcast_create')).toBe(true);
    }

    for (const role of ['viewer', 'support', 'finance', 'operator'] as const) {
      expect(hasAdminPermission(role, 'notification_broadcast_create')).toBe(false);
    }
  });

  it('grants support ticket read only to backend-approved support roles', () => {
    for (const role of ['support', 'admin', 'super_admin', 'owner/super_admin'] as const) {
      expect(hasAdminPermission(role, 'support_ticket_read')).toBe(true);
    }

    for (const role of ['viewer', 'finance', 'operator'] as const) {
      expect(hasAdminPermission(role, 'support_ticket_read')).toBe(false);
    }
  });
});
