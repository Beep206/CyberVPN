import { SecurityReviewQueueConsole } from '@/features/security/components/security-review-queue-console';
import { getSecurityPageMetadata } from '@/features/security/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getSecurityPageMetadata(locale, 'reviewQueue');
}

export default function SecurityReviewQueuePage() {
  return <SecurityReviewQueueConsole />;
}
