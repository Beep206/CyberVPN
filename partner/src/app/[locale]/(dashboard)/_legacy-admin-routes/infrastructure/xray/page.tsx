import { XrayConsole } from '@/features/infrastructure/components/xray-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'xray');
}

export default function InfrastructureXrayPage() {
  return <XrayConsole />;
}
