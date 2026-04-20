import { connection } from 'next/server';
import { CustomerDetail } from '@/features/customers/components/customer-detail';
import { getCustomersPageMetadata } from '@/features/customers/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; userId: string }>;
}) {
  const { locale } = await params;
  return getCustomersPageMetadata(locale, 'detail');
}

export default async function CustomerDetailPage({
  params,
}: {
  params: Promise<{ userId: string }>;
}) {
  await connection();
  const { userId } = await params;
  return <CustomerDetail userId={userId} />;
}
