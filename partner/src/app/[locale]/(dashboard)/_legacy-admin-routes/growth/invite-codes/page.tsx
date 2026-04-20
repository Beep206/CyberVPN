import { InviteCodesConsole } from '@/features/growth/components/invite-codes-console';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'inviteCodes');
}

export default function GrowthInviteCodesPage() {
  return <InviteCodesConsole />;
}
