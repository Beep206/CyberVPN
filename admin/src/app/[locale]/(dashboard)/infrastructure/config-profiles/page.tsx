import { ConfigProfilesConsole } from '@/features/infrastructure/components/config-profiles-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'configProfiles');
}

export default function InfrastructureConfigProfilesPage() {
  return <ConfigProfilesConsole />;
}
