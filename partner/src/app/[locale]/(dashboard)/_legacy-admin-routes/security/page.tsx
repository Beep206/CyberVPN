import { SecurityOverview } from '@/features/security/components/security-overview';
import { getSecurityPageMetadata } from '@/features/security/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getSecurityPageMetadata(locale, 'overview');
}

export default function SecurityPage() {
  return <SecurityOverview />;
}
