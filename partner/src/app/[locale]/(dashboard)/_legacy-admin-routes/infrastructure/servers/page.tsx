import { ServersConsole } from '@/features/infrastructure/components/servers-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'servers');
}

export default function InfrastructureServersPage() {
  return <ServersConsole />;
}
