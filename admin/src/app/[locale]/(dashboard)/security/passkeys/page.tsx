import { SecurityPasskeysConsole } from '@/features/security/components/security-passkeys-console';
import { getSecurityPageMetadata } from '@/features/security/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getSecurityPageMetadata(locale, 'passkeys');
}

export default function SecurityPasskeysPage() {
  return <SecurityPasskeysConsole />;
}
