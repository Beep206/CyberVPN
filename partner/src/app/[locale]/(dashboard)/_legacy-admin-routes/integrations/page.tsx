import { IntegrationsOverview } from '@/features/integrations/components/integrations-overview';
import { getIntegrationsPageMetadata } from '@/features/integrations/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getIntegrationsPageMetadata(locale, 'overview');
}

export default function IntegrationsPage() {
  return <IntegrationsOverview />;
}
