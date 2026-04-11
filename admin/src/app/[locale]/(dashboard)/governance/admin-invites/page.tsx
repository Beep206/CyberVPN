import { AdminInvitesConsole } from '@/features/governance/components/admin-invites-console';
import { getGovernancePageMetadata } from '@/features/governance/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getGovernancePageMetadata(locale, 'adminInvites');
}

export default function GovernanceAdminInvitesPage() {
  return <AdminInvitesConsole />;
}
