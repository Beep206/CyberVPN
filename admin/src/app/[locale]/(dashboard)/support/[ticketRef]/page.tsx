import { SupportConsole } from '@/features/support/components/support-console';
import { getSupportPageMetadata } from '@/features/support/lib/page-metadata';

type SupportConversationSearchParams = Promise<Record<string, string | string[] | undefined>>;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; ticketRef: string }>;
}) {
  const { locale } = await params;
  return getSupportPageMetadata(locale, 'detail');
}

export default async function SupportConversationPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string; ticketRef: string }>;
  searchParams: SupportConversationSearchParams;
}) {
  const { ticketRef } = await params;

  return (
    <SupportConsole
      initialSearchParams={await searchParams}
      initialTicketRef={decodeURIComponent(ticketRef)}
    />
  );
}
