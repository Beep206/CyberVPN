import { SecurityPostureConsole } from '@/features/security/components/security-posture-console';
import { getSecurityPageMetadata } from '@/features/security/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getSecurityPageMetadata(locale, 'posture');
}

export default function SecurityPosturePage() {
  return <SecurityPostureConsole />;
}
