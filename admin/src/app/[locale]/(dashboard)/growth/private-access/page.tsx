import { GrowthPrivateAccessConsole } from '@/features/growth/components/growth-v6-operations-console';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

type GrowthPrivateAccessPageProps = {
  params: Promise<{
    locale: string;
  }>;
};

export async function generateMetadata({ params }: GrowthPrivateAccessPageProps) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'privateAccess');
}

export default function GrowthPrivateAccessPage() {
  return <GrowthPrivateAccessConsole />;
}
