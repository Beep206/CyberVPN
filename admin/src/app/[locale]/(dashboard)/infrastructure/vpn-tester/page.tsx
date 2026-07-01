import { VpnTesterConsole } from '@/features/infrastructure/components/vpn-tester-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'vpnTester');
}

export default function InfrastructureVpnTesterPage() {
  return <VpnTesterConsole />;
}
