import { GrowthNotificationsConsole } from '@/features/growth/components/growth-overview';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'notifications');
}

export default function GrowthNotificationsPage() {
  return <GrowthNotificationsConsole />;
}
