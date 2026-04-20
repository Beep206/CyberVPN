import { WithdrawalsConsole } from '@/features/commerce/components/withdrawals-console';
import { getCommercePageMetadata } from '@/features/commerce/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getCommercePageMetadata(locale, 'withdrawals');
}

export default function CommerceWithdrawalsPage() {
  return <WithdrawalsConsole />;
}
