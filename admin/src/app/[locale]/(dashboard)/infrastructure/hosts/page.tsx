import { HostsConsole } from '@/features/infrastructure/components/hosts-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'hosts');
}

export default function InfrastructureHostsPage() {
  return <HostsConsole />;
}
