import { MessagingConsole } from '@/features/messaging/components/messaging-console';
import { getMessagingPageMetadata } from '@/features/messaging/lib/page-metadata';

type MessagingConversationSearchParams = Promise<Record<string, string | string[] | undefined>>;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; conversationRef: string }>;
}) {
  const { locale } = await params;
  return getMessagingPageMetadata(locale, 'detail');
}

export default async function MessagingConversationPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string; conversationRef: string }>;
  searchParams: MessagingConversationSearchParams;
}) {
  const { conversationRef } = await params;

  return (
    <MessagingConsole
      initialConversationRef={decodeURIComponent(conversationRef)}
      initialSearchParams={await searchParams}
    />
  );
}
