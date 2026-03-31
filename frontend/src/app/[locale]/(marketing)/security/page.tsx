import { getTranslations } from 'next-intl/server';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
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
    }, {
        locale,
        canonicalPath: '/security',
        routeType: 'public',
    });
}

export default async function SecurityPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;

    return (
        <main className="min-h-screen bg-black text-terminal-text selection:bg-neon-cyan/30 flex flex-col font-mono">
            <PublicTerminalHeader locale={locale} />
            
            <section className="flex-1 relative w-full pt-16">
                <SecurityDashboard />
            </section>

            <Footer locale={locale} />
        </main>
    );
}
