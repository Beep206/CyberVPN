import { InboundsConsole } from '@/features/infrastructure/components/inbounds-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'inbounds');
}

export default function InfrastructureInboundsPage() {
  return <InboundsConsole />;
}
