import { MiniAppDiagnosticsClient } from './MiniAppDiagnosticsClient';

export default async function MiniAppDiagnosticsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return <MiniAppDiagnosticsClient locale={locale} />;
}
