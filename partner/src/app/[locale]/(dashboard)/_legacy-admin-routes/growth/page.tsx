import { GrowthOverview } from '@/features/growth/components/growth-overview';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'overview');
}

export default function GrowthPage() {
  return <GrowthOverview />;
}
