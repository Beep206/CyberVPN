import { NodePluginsConsole } from '@/features/infrastructure/components/node-plugins-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'nodePlugins');
}

export default function InfrastructureNodePluginsPage() {
  return <NodePluginsConsole />;
}
