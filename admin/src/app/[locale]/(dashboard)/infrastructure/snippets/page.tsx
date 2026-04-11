import { SnippetsConsole } from '@/features/infrastructure/components/snippets-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'snippets');
}

export default function InfrastructureSnippetsPage() {
  return <SnippetsConsole />;
}
