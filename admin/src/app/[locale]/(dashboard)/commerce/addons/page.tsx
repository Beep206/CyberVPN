import { AddonsConsole } from '@/features/commerce/components/addons-console';
import { getCommercePageMetadata } from '@/features/commerce/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getCommercePageMetadata(locale, 'addons');
}

export default function CommerceAddonsPage() {
  return <AddonsConsole />;
}
