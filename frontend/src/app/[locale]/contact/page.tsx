import { getTranslations } from 'next-intl/server';
import { ContactForm } from '@/widgets/contact-form';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Contact' });

    return {
        title: `${t('title')} | CyberVPN`,
        description: t('subtitle'),
    };
}

export default async function ContactPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Contact' });

    return (
        <main className="min-h-screen relative overflow-hidden bg-background">

            {/* The Main Split Screen Form */}
            <div className="relative z-10 w-full h-full">
                <ContactForm />
            </div>

        </main>
    );
}
