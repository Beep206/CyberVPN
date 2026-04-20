import { SecurityTwoFactorConsole } from '@/features/security/components/security-two-factor-console';
import { getSecurityPageMetadata } from '@/features/security/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getSecurityPageMetadata(locale, 'twoFactor');
}

export default function SecurityTwoFactorPage() {
  return <SecurityTwoFactorConsole />;
}
