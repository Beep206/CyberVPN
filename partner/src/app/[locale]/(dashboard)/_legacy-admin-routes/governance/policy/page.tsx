import { PolicyConsole } from '@/features/governance/components/policy-console';
import { getGovernancePageMetadata } from '@/features/governance/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGovernancePageMetadata(locale, 'policy');
}

export default function GovernancePolicyPage() {
  return <PolicyConsole />;
}
