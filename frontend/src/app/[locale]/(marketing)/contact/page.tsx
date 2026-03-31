import { getTranslations } from 'next-intl/server';
import { ContactForm } from '@/widgets/contact-form';
import { Footer } from '@/widgets/footer';
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

export default function ContactPage() {

    return (
        <div className="flex min-h-screen flex-col bg-background">
            <PublicTerminalHeader />
            
            <main className="flex-1 relative overflow-hidden bg-background">
                {/* The Main Split Screen Form */}
                <div className="relative z-10 w-full h-full">
                    <ContactForm />
                </div>
            </main>

            <Footer />
        </div>
    );
}
