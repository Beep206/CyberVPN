import { RemnawaveOperationsConsole } from '@/features/infrastructure/components/remnawave-operations-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'remnawave');
}

export default function InfrastructureRemnawavePage() {
  return <RemnawaveOperationsConsole />;
}
