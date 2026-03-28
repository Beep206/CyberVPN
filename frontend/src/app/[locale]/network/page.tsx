import { getTranslations } from 'next-intl/server';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
import { NetworkDashboard } from '@/widgets/servers/network-dashboard';

export async function generateMetadata() {
    const t = await getTranslations({ locale, namespace: 'Network' });
    
    return {
        title: `${t('title')} | CyberVPN`,
        description: t('description'),
    };
}

export default function ServersPage() {

    return (
        <main className="min-h-screen bg-black text-terminal-text selection:bg-neon-cyan/30 flex flex-col font-mono overflow-x-hidden">
            <TerminalHeader />
            
            <section className="flex-1 relative w-full pt-16">
                <NetworkDashboard />
            </section>
            
            <Footer />
        </main>
    );
}
