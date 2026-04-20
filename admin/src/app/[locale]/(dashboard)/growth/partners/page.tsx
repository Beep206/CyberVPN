import { PartnerOperationsConsole } from '@/features/growth/components/partner-operations-console';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'partners');
}

export default function GrowthPartnersPage() {
  return <PartnerOperationsConsole />;
}
