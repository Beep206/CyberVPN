import { PushOpsConsole } from '@/features/integrations/components/push-ops-console';
import { getIntegrationsPageMetadata } from '@/features/integrations/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getIntegrationsPageMetadata(locale, 'push');
}

export default function IntegrationsPushPage() {
  return <PushOpsConsole />;
}
