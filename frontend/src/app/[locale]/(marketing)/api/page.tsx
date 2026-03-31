import { getTranslations } from 'next-intl/server';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { ApiDashboard } from '@/widgets/api/api-dashboard';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Api' });
    
    return withSiteMetadata({
        title: `${t('title')} | CyberVPN`,
        description: t('description'),
    }, {
        locale,
        canonicalPath: '/api',
        routeType: 'public',
    });
}

export default function ApiPage() {

    return (
        <main className="min-h-screen bg-black text-terminal-text selection:bg-neon-pink/30 flex flex-col font-mono">
            <PublicTerminalHeader />
            
            <section className="flex-1 relative w-full pt-16">
                <ApiDashboard />
            </section>

            <Footer />
        </main>
    );
}
