import { CommerceOverview } from '@/features/commerce/components/commerce-overview';
import { getCommercePageMetadata } from '@/features/commerce/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getCommercePageMetadata(locale, 'overview');
}

export default function CommercePage() {
  return <CommerceOverview />;
}
