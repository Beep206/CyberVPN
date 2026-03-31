import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { DeleteAccountClient } from './delete-account-client';

export default async function DeleteAccountPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  return (
    <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
      <PublicTerminalHeader locale={locale} />
      <DeleteAccountClient />
      <Footer locale={locale} />
    </main>
  );
}
