import { InfrastructureOverview } from '@/features/infrastructure/components/infrastructure-overview';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'overview');
}

export default function InfrastructurePage() {
  return <InfrastructureOverview />;
}
