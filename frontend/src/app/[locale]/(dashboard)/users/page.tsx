import { notFound } from 'next/navigation';
import { canStage1CustomerDashboardSurfaceAccess } from '@/shared/lib/stage1-customer-surface-policy';

export default function UsersPage() {
  if (!canStage1CustomerDashboardSurfaceAccess('users')) {
    notFound();
  }

  return null;
}
