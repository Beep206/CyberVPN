import { WalletOpsConsole } from '@/features/commerce/components/wallet-ops-console';
import { getCommercePageMetadata } from '@/features/commerce/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getCommercePageMetadata(locale, 'wallets');
}

export default function CommerceWalletsPage() {
  return <WalletOpsConsole />;
}
