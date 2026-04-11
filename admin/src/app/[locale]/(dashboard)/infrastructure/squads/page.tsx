import { SquadsConsole } from '@/features/infrastructure/components/squads-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'squads');
}

export default function InfrastructureSquadsPage() {
  return <SquadsConsole />;
}
