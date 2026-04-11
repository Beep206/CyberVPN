import { PlansConsole } from '@/features/commerce/components/plans-console';
import { getCommercePageMetadata } from '@/features/commerce/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getCommercePageMetadata(locale, 'plans');
}

export default function CommercePlansPage() {
  return <PlansConsole />;
}
