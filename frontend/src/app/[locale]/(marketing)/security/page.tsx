import { getTranslations } from 'next-intl/server';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
import { SecurityDashboard } from '@/widgets/security/security-dashboard';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Security' });
    
    return withSiteMetadata({
        title: `${t('title')} | CyberVPN`,
        description: t('description'),
    });
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
