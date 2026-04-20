import { PaymentsConsole } from '@/features/commerce/components/payments-console';
import { getCommercePageMetadata } from '@/features/commerce/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getCommercePageMetadata(locale, 'payments');
}

export default function CommercePaymentsPage() {
  return <PaymentsConsole />;
}
