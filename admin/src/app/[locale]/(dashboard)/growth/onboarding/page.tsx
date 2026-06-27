import { GrowthOnboardingConsole } from '@/features/growth/components/growth-v6-operations-console';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

type GrowthOnboardingPageProps = {
  params: Promise<{
    locale: string;
  }>;
};

export async function generateMetadata({ params }: GrowthOnboardingPageProps) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'onboarding');
}

export default function GrowthOnboardingPage() {
  return <GrowthOnboardingConsole />;
}
