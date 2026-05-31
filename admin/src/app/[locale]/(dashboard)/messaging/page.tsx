import { MessagingConsole } from '@/features/messaging/components/messaging-console';
import { getMessagingPageMetadata } from '@/features/messaging/lib/page-metadata';

type MessagingPageSearchParams = Promise<Record<string, string | string[] | undefined>>;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getMessagingPageMetadata(locale, 'inbox');
}

export default async function MessagingInboxPage({
  searchParams,
}: {
  searchParams: MessagingPageSearchParams;
}) {
  return <MessagingConsole initialSearchParams={await searchParams} />;
}
