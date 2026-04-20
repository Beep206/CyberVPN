import { SecurityAntiPhishingConsole } from '@/features/security/components/security-antiphishing-console';
import { getSecurityPageMetadata } from '@/features/security/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getSecurityPageMetadata(locale, 'antiPhishing');
}

export default function SecurityAntiPhishingPage() {
  return <SecurityAntiPhishingConsole />;
}
