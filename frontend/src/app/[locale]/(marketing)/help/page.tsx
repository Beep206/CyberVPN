import type { BreadcrumbList, FAQPage } from 'schema-dts';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { JsonLd } from '@/shared/lib/json-ld';
import {
  buildBreadcrumbListStructuredData,
  buildFaqPageStructuredData,
} from '@/shared/lib/structured-data';
import { HelpHero } from '@/widgets/help-hero';
import { HelpCategories } from '@/widgets/help-categories';
import { HelpFaq } from '@/widgets/help-faq';
import { getHelpKnowledge } from '@/widgets/help-faq-server';
import { HelpContact } from '@/widgets/help-contact';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'HelpCenter' });

    return withSiteMetadata({
        title: t('meta_title'),
        description: t('meta_description'),
    }, {
        locale,
        canonicalPath: '/help',
        routeType: 'public',
    });
}

export default async function HelpCenterPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    setRequestLocale(locale);
    const [t, categories] = await Promise.all([
        getTranslations({ locale, namespace: 'HelpCenter' }),
        getHelpKnowledge(),
    ]);
    const pageTitle = t('meta_title');
    const pageDescription = t('meta_description');
    const faqStructuredData = buildFaqPageStructuredData({
        locale,
        path: '/help',
        title: pageTitle,
        description: pageDescription,
        faqs: categories.flatMap((category) => category.faqs),
    });
    const breadcrumbStructuredData = buildBreadcrumbListStructuredData({
        locale,
        items: [
            { name: 'Home', path: '/' },
            { name: pageTitle, path: '/help' },
        ],
    });

    return (
        <>
            <main className="flex flex-col min-h-screen selection:bg-neon-pink selection:text-black">
                <PublicTerminalHeader />
                <HelpHero />
                <div className="container mx-auto px-4 py-16 space-y-24 z-10 relative">
                    <HelpCategories />
                    <HelpFaq />
                    <HelpContact />
                </div>
                <Footer />
            </main>

            <JsonLd<FAQPage> data={faqStructuredData} />
            <JsonLd<BreadcrumbList> data={breadcrumbStructuredData} />
        </>
    );
}
