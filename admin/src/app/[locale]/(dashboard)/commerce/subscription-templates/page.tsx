import { SubscriptionTemplatesConsole } from '@/features/commerce/components/subscription-templates-console';
import { getCommercePageMetadata } from '@/features/commerce/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getCommercePageMetadata(locale, 'subscriptionTemplates');
}

export default function CommerceSubscriptionTemplatesPage() {
  return <SubscriptionTemplatesConsole />;
}
