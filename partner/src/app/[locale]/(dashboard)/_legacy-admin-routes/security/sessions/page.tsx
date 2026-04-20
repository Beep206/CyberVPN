import { SecuritySessionsConsole } from '@/features/security/components/security-sessions-console';
import { getSecurityPageMetadata } from '@/features/security/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getSecurityPageMetadata(locale, 'sessions');
}

export default function SecuritySessionsPage() {
  return <SecuritySessionsConsole />;
}
