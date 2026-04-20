import { GovernanceOverview } from '@/features/governance/components/governance-overview';
import { getGovernancePageMetadata } from '@/features/governance/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGovernancePageMetadata(locale, 'overview');
}

export default function GovernancePage() {
  return <GovernanceOverview />;
}
