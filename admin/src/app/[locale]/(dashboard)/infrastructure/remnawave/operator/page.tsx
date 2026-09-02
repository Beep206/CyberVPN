import {
  RemnawaveOperatorConsole,
  type OperatorSection,
} from '@/features/infrastructure/components/remnawave-operator-console';
import { getInfrastructurePageMetadata } from '@/features/infrastructure/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getInfrastructurePageMetadata(locale, 'remnawaveOperator');
}

function parseInitialSection(
  value: string | string[] | undefined,
): OperatorSection {
  const candidate = Array.isArray(value) ? value[0] : value;
  const sections: readonly OperatorSection[] = [
    'tags',
    'geoCheck',
    'integrations',
    'sharedLists',
    'snippets',
  ];
  return sections.find((section) => section === candidate) ?? 'tags';
}

export default async function InfrastructureRemnawaveOperatorPage({
  searchParams,
}: {
  searchParams: Promise<{ section?: string | string[] }>;
}) {
  const { section } = await searchParams;
  return <RemnawaveOperatorConsole initialSection={parseInitialSection(section)} />;
}
