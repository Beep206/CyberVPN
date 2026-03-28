import { getTranslations } from 'next-intl/server';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
import { ApiDashboard } from '@/widgets/api/api-dashboard';

export async function generateMetadata() {
    const t = await getTranslations({ locale, namespace: 'Api' });
    
    return {
        title: `${t('title')} | CyberVPN`,
        description: t('description'),
    };
}

export default function ApiPage() {

    return (
        <main className="min-h-screen bg-black text-terminal-text selection:bg-neon-pink/30 flex flex-col font-mono">
            <TerminalHeader />
            
            <section className="flex-1 relative w-full pt-16">
                <ApiDashboard />
            </section>

            <Footer />
        </main>
    );
}
