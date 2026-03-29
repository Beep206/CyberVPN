import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
import { DeleteAccountClient } from './delete-account-client';

export default function DeleteAccountPage() {
  return (
    <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
      <TerminalHeader />
      <DeleteAccountClient />
      <Footer />
    </main>
  );
}
