import { getTranslations } from 'next-intl/server';
import { ContactForm } from '@/widgets/contact-form';
import { Footer } from '@/widgets/footer';
import { OfficialSupportRoutingPanel } from '@/widgets/official-support-routing-panel';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Contact' });

    return withSiteMetadata({
        title: `${t('title')} | CyberVPN`,
        description: t('subtitle'),
    }, {
        locale,
        canonicalPath: '/contact',
        routeType: 'public',
    });
}

export default async function ContactPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;

    return (
        <div className="flex min-h-screen flex-col bg-background">
            <PublicTerminalHeader locale={locale} />
            
            <main className="flex-1 relative overflow-hidden bg-background">
                <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-8 md:px-6">
                    <OfficialSupportRoutingPanel locale={locale} />
                    <ContactForm />
                </div>
            </main>

            <Footer locale={locale} />
        </div>
    );
}
