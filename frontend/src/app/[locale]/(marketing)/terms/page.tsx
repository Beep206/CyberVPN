import { getTranslations } from 'next-intl/server';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { TermsDashboard } from '@/widgets/terms/terms-dashboard';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Terms' });
    
    return withSiteMetadata({
        title: `${t('title')} | CyberVPN`,
        description: t('description'),
    }, {
        locale,
        canonicalPath: '/terms',
        routeType: 'public',
    });
}

export default function TermsPage() {

    return (
        <main className="min-h-screen bg-black text-terminal-text selection:bg-warning/30 flex flex-col font-mono">
            <PublicTerminalHeader />
            
            <section className="flex-1 relative w-full pt-16">
                <TermsDashboard />
            </section>

            <Footer />
        </main>
    );
}
