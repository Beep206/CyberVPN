import { getTranslations } from 'next-intl/server';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
import { StatusDashboard } from '@/widgets/status/status-dashboard';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Status' });

    return {
        title: `${t('title')} | CyberVPN`,
        description: t('subtitle'),
    };
}

export default async function StatusPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Status' });

    return (
        <div className="flex min-h-screen flex-col bg-background relative overflow-hidden">
            <TerminalHeader />
            
            <main className="flex-1 relative w-full h-full flex flex-col">
                <StatusDashboard />
            </main>

            {/* <Footer /> - The footer might overlap the 3D scene in full-height mode, 
                let's keep it but ensure the status dashboard manages its own bottom padding if needed. */}
            <div className="relative z-20 bg-background/80 backdrop-blur-md border-t border-white/5">
                <Footer />
            </div>
        </div>
    );
}
