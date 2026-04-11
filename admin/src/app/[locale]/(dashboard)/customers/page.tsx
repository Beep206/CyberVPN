import { CustomersDirectory } from '@/features/customers/components/customers-directory';
import { getCustomersPageMetadata } from '@/features/customers/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getCustomersPageMetadata(locale, 'directory');
}

export default function CustomersPage() {
  return <CustomersDirectory />;
}
