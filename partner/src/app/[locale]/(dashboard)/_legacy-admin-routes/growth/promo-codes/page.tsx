import { PromoCodesConsole } from '@/features/growth/components/promo-codes-console';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'promoCodes');
}

export default function GrowthPromoCodesPage() {
  return <PromoCodesConsole />;
}
