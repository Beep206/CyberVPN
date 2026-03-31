import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { DeleteAccountClient } from './delete-account-client';

export default function DeleteAccountPage() {
  return (
    <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
      <PublicTerminalHeader />
      <DeleteAccountClient />
      <Footer />
    </main>
  );
}
