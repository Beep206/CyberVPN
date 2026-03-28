import { getTranslations } from 'next-intl/server';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
import { SecurityDashboard } from '@/widgets/security/security-dashboard';

export async function generateMetadata() {
    const t = await getTranslations({ locale, namespace: 'Security' });
    
    return {
        title: `${t('title')} | CyberVPN`,
        description: t('description'),
    };
}

export default function SecurityPage() {

    return (
        <main className="min-h-screen bg-black text-terminal-text selection:bg-neon-cyan/30 flex flex-col font-mono">
            <TerminalHeader />
            
            <section className="flex-1 relative w-full pt-16">
                <SecurityDashboard />
            </section>

            <Footer />
        </main>
    );
}
