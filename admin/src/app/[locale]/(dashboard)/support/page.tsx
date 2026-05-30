import { SupportConsole } from '@/features/support/components/support-console';
import { getSupportPageMetadata } from '@/features/support/lib/page-metadata';

type SupportPageSearchParams = Promise<Record<string, string | string[] | undefined>>;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getSupportPageMetadata(locale, 'inbox');
}

export default async function SupportInboxPage({
  searchParams,
}: {
  searchParams: SupportPageSearchParams;
}) {
  return <SupportConsole initialSearchParams={await searchParams} />;
}
