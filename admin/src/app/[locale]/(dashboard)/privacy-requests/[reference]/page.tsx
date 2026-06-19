import { PrivacyRequestConsole } from '@/features/privacy-requests/components/privacy-request-console';

type PrivacyRequestDetailPageParams = Promise<{ reference: string }>;
type PrivacyRequestDetailPageSearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function PrivacyRequestDetailPage({
  params,
  searchParams,
}: {
  params: PrivacyRequestDetailPageParams;
  searchParams: PrivacyRequestDetailPageSearchParams;
}) {
  const { reference } = await params;
  return (
    <PrivacyRequestConsole
      initialReference={decodeURIComponent(reference)}
      initialSearchParams={await searchParams}
    />
  );
}
