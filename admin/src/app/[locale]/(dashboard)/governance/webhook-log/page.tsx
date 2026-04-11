import { WebhookLogConsole } from '@/features/governance/components/webhook-log-console';
import { getGovernancePageMetadata } from '@/features/governance/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGovernancePageMetadata(locale, 'webhookLog');
}

export default function GovernanceWebhookLogPage() {
  return <WebhookLogConsole />;
}
