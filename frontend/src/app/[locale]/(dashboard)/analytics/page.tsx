import { notFound } from 'next/navigation';
import { canStage1CustomerDashboardSurfaceAccess } from '@/shared/lib/stage1-customer-surface-policy';

export default function AnalyticsPage() {
  if (!canStage1CustomerDashboardSurfaceAccess('analytics')) {
    notFound();
  }

  return null;
}
