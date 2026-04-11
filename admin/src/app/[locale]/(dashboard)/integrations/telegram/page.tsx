import { TelegramOpsConsole } from '@/features/integrations/components/telegram-ops-console';
import { getIntegrationsPageMetadata } from '@/features/integrations/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getIntegrationsPageMetadata(locale, 'telegram');
}

export default function IntegrationsTelegramPage() {
  return <TelegramOpsConsole />;
}
