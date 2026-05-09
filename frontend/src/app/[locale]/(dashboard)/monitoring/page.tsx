import { notFound } from 'next/navigation';
import { canStage1CustomerDashboardSurfaceAccess } from '@/shared/lib/stage1-customer-surface-policy';

export default function MonitoringPage() {
  if (!canStage1CustomerDashboardSurfaceAccess('monitoring')) {
    notFound();
  }

  return null;
}
