import { GrowthFxConsole } from '@/features/growth/components/growth-v6-operations-console';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

type GrowthFxPageProps = {
  params: Promise<{
    locale: string;
  }>;
};

export async function generateMetadata({ params }: GrowthFxPageProps) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'fx');
}

export default function GrowthFxPage() {
  return <GrowthFxConsole />;
}
