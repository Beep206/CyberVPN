import { PrivacyRequestConsole } from '@/features/privacy-requests/components/privacy-request-console';

type PrivacyRequestsPageSearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function PrivacyRequestsPage({
  searchParams,
}: {
  searchParams: PrivacyRequestsPageSearchParams;
}) {
  return <PrivacyRequestConsole initialSearchParams={await searchParams} />;
}
