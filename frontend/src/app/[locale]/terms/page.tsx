import { getTranslations } from 'next-intl/server';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
import { TermsDashboard } from '@/widgets/terms/terms-dashboard';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Terms' });
    
    return {
        title: `${t('title')} | CyberVPN`,
        description: t('description'),
    };
}

export default async function TermsPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Terms' });

    return (
        <main className="min-h-screen bg-black text-terminal-text selection:bg-warning/30 flex flex-col font-mono">
            <TerminalHeader />
            
            <section className="flex-1 relative w-full pt-16">
                <TermsDashboard />
            </section>

            <Footer />
        </main>
    );
}
