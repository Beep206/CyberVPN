import { getTranslations } from 'next-intl/server';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
import { FeaturesDashboard } from '@/widgets/features/features-dashboard';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Features' });
    
    return withSiteMetadata({
        title: `${t('title')} | CyberVPN`,
        description: t('description'),
    });
}

export default function FeaturesPage() {

    return (
        <main className="min-h-screen bg-black text-terminal-text selection:bg-neon-cyan/30 flex flex-col font-mono overflow-x-hidden">
            <TerminalHeader />
            
            <section className="flex-1 relative w-full pt-16">
                <FeaturesDashboard/>
            </section>
            
            <Footer />
        </main>
    );
}
