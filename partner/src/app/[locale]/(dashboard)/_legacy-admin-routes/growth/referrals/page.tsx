import { ReferralSignalsConsole } from '@/features/growth/components/referral-signals-console';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'referrals');
}

export default function GrowthReferralsPage() {
  return <ReferralSignalsConsole />;
}
