import { RuleBuilderShell } from '@/features/growth-rule-builder/components/rule-builder-shell';
import { getGrowthPageMetadata } from '@/features/growth/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGrowthPageMetadata(locale, 'rules');
}

export default function GrowthRulesPage() {
  return <RuleBuilderShell />;
}
