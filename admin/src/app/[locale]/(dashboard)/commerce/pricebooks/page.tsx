import { PricebooksConsole } from '@/features/commerce/components/pricebooks-console';
import { getCommercePageMetadata } from '@/features/commerce/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getCommercePageMetadata(locale, 'pricebooks');
}

export default function CommercePricebooksPage() {
  return <PricebooksConsole />;
}
