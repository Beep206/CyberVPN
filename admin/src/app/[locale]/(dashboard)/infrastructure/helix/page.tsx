import { HelixConsole } from '@/features/infrastructure/components/helix-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'helix');
}

export default function InfrastructureHelixPage() {
  return <HelixConsole />;
}
