import { RealtimeOpsConsole } from '@/features/integrations/components/realtime-ops-console';
import { getIntegrationsPageMetadata } from '@/features/integrations/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getIntegrationsPageMetadata(locale, 'realtime');
}

export default function IntegrationsRealtimePage() {
  return <RealtimeOpsConsole />;
}
