import { getTranslations } from 'next-intl/server';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
import { DownloadDashboard } from '@/widgets/download/download-dashboard';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Download' });

    return {
        title: `${t('title')} | CyberVPN`,
        description: t('subtitle'),
    };
}

export default async function DownloadPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Download' });

    return (
        <div className="flex min-h-screen flex-col bg-background relative overflow-hidden">
            <TerminalHeader />
            
            <main className="flex-1 relative w-full h-full flex flex-col">
                <DownloadDashboard />
            </main>

            <div className="relative z-20 bg-background/80 backdrop-blur-md border-t border-white/5">
                <Footer />
            </div>
        </div>
    );
}
