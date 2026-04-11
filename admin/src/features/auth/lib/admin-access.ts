import type { User } from '@/lib/api/auth';
import { hasAdminAccess as hasSharedAdminAccess } from '@/shared/lib/admin-rbac';

export const ACCESS_DENIED_ERROR_CODE = 'access_denied';

export function hasAdminAccess(role: string | null | undefined): boolean {
  return hasSharedAdminAccess(role);
}

export function isAdminUser(user: Pick<User, 'role'> | null | undefined): boolean {
  return hasAdminAccess(user?.role);
}

export function buildLocalizedAccessDeniedLoginPath(locale: string): string {
  return `/${locale}/login?error=${ACCESS_DENIED_ERROR_CODE}`;
}
