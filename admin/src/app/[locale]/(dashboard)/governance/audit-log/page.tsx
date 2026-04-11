import { AuditLogConsole } from '@/features/governance/components/audit-log-console';
import { getGovernancePageMetadata } from '@/features/governance/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGovernancePageMetadata(locale, 'auditLog');
}

export default function GovernanceAuditLogPage() {
  return <AuditLogConsole />;
}
