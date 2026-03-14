import { getTranslations, setRequestLocale } from 'next-intl/server';
import { DocsContainer } from '@/widgets/docs-container';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Docs' });

    return {
        title: t('meta_title'),
        description: t('meta_description'),
    };
}

export default async function DocsPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    setRequestLocale(locale);

    return (
        <main className="w-full h-full relative">
            <div className="max-w-[1440px] mx-auto w-full">
                <DocsContainer />
            </div>
        </main>
    );
}
