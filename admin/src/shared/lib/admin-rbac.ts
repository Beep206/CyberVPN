import type { User } from '@/lib/api/auth';

export const ADMIN_ROLES = [
  'viewer',
  'support',
  'operator',
  'admin',
  'super_admin',
] as const;

export type AdminRole = (typeof ADMIN_ROLES)[number];

export const ADMIN_PERMISSIONS = [
  'user_read',
  'user_create',
  'user_update',
  'user_delete',
  'server_read',
  'server_create',
  'server_update',
  'server_delete',
  'payment_read',
  'payment_create',
  'monitoring_read',
  'audit_read',
  'webhook_read',
  'manage_admins',
  'manage_plans',
  'manage_invites',
  'subscription_create',
  'view_analytics',
] as const;

export type AdminPermission = (typeof ADMIN_PERMISSIONS)[number];

export const ADMIN_PERMISSION_MATRIX: Record<
  AdminRole,
  readonly AdminPermission[]
> = {
  super_admin: [...ADMIN_PERMISSIONS],
  admin: [
    'user_read',
    'user_create',
    'user_update',
    'user_delete',
    'server_read',
    'server_create',
    'server_update',
    'server_delete',
    'payment_read',
    'payment_create',
    'monitoring_read',
    'audit_read',
    'webhook_read',
    'manage_plans',
    'manage_invites',
    'subscription_create',
    'view_analytics',
  ],
  operator: [
    'user_read',
    'user_create',
    'user_update',
    'server_read',
    'server_create',
    'server_update',
    'payment_read',
    'payment_create',
    'monitoring_read',
    'subscription_create',
    'view_analytics',
  ],
  support: [
    'user_read',
    'user_update',
    'server_read',
    'monitoring_read',
  ],
  viewer: [
    'user_read',
    'server_read',
    'monitoring_read',
    'view_analytics',
  ],
} as const;

const ADMIN_CONSOLE_ROLES = new Set<AdminRole>(['admin', 'super_admin']);

export function isAdminRole(
  role: User['role'] | string | null | undefined,
): role is AdminRole {
  return Boolean(role && ADMIN_ROLES.includes(role as AdminRole));
}

export function hasAdminAccess(
  role: User['role'] | string | null | undefined,
): boolean {
  return isAdminRole(role) && ADMIN_CONSOLE_ROLES.has(role);
}

export function getAdminRolePermissions(
  role: User['role'] | string | null | undefined,
): readonly AdminPermission[] {
  if (!isAdminRole(role)) {
    return [];
  }

  return ADMIN_PERMISSION_MATRIX[role];
}

export function hasAdminPermission(
  role: User['role'] | string | null | undefined,
  permission: AdminPermission,
): boolean {
  return getAdminRolePermissions(role).includes(permission);
}

