import { CustomerSiteModeConsole } from '@/features/growth/components/customer-site-mode-console';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

type GrowthSiteModePageProps = {
  params: Promise<{
    locale: string;
  }>;
};

export async function generateMetadata({ params }: GrowthSiteModePageProps) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'siteMode');
}

export default function GrowthSiteModePage() {
  return <CustomerSiteModeConsole />;
}
