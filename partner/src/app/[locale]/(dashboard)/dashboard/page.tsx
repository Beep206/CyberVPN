import { PartnerDashboardPage } from '@/features/partner-portal-state/components/partner-dashboard-page';

export default async function Dashboard({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  await params;

  return <PartnerDashboardPage />;
}
