import { RemnawaveConnectionsConsole } from '@/features/infrastructure/components/remnawave-connections-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'remnawaveConnections');
}

export default function InfrastructureRemnawaveConnectionsPage() {
  return <RemnawaveConnectionsConsole />;
}
