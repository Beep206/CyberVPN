import { getTranslations, setRequestLocale } from 'next-intl/server';
import { HelpHero } from '@/widgets/help-hero';
import { HelpCategories } from '@/widgets/help-categories';
import { HelpFaq } from '@/widgets/help-faq';
import { HelpContact } from '@/widgets/help-contact';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'HelpCenter' });

    return {
        title: t('meta_title'),
        description: t('meta_description'),
    };
}

export default async function HelpCenterPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    setRequestLocale(locale);

    return (
        <main className="flex flex-col min-h-screen selection:bg-neon-pink selection:text-black">
            <TerminalHeader />
            <HelpHero />
            <div className="container mx-auto px-4 py-16 space-y-24 z-10 relative">
                <HelpCategories />
                <HelpFaq />
                <HelpContact />
            </div>
            <Footer />
        </main>
    );
}
