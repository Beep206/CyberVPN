import { GrowthCampaignsConsole } from '@/features/growth/components/growth-campaigns-console';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

type GrowthCampaignsPageProps = {
  params: Promise<{
    locale: string;
  }>;
};

export async function generateMetadata({ params }: GrowthCampaignsPageProps) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'campaigns');
}

export default function GrowthCampaignsPage() {
  return <GrowthCampaignsConsole />;
}
