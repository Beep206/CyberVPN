import { getTranslations } from 'next-intl/server';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
import { PrivacyDashboard } from '@/widgets/privacy/privacy-dashboard';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Privacy' });
    
    return {
        title: `${t('title')} | CyberVPN`,
        description: t('description'),
    };
}

export default async function PrivacyPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Privacy' });

    return (
        <main className="min-h-screen bg-black text-terminal-text selection:bg-neon-pink/30 flex flex-col font-mono">
            <TerminalHeader />
            
            <section className="flex-1 relative w-full pt-16">
                <PrivacyDashboard />
            </section>

            <Footer />
        </main>
    );
}
