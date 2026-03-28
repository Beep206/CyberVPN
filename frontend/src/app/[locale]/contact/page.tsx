import { getTranslations } from 'next-intl/server';
import { ContactForm } from '@/widgets/contact-form';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';

export async function generateMetadata() {
    const t = await getTranslations({ locale, namespace: 'Contact' });

    return {
        title: `${t('title')} | CyberVPN`,
        description: t('subtitle'),
    };
}

export default function ContactPage() {

    return (
        <div className="flex min-h-screen flex-col bg-background">
            <TerminalHeader />
            
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
